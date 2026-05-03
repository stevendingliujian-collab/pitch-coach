import json
import os
import re
import httpx
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import get_settings
from app.core.desensitize import DesensitizeContext

settings = get_settings()

_client: AsyncOpenAI | None = None

# Dashscope domains that must bypass any system proxy
_NO_PROXY_HOSTS = {"dashscope.aliyuncs.com", "coding.dashscope.aliyuncs.com"}


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        # Direct transport (no proxy) for dashscope; system proxy for everything else
        system_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        direct = httpx.AsyncHTTPTransport()  # no proxy
        mounts: dict = {f"https://{h}": direct for h in _NO_PROXY_HOSTS}
        if system_proxy:
            mounts["all://"] = httpx.AsyncHTTPTransport(proxy=httpx.Proxy(system_proxy))
        http_client = httpx.AsyncClient(mounts=mounts, timeout=180)
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            http_client=http_client,
        )
    return _client

SYSTEM_PROMPT = """你是一位拥有 15 年项目投标经验的述标专家，擅长非标自动化、系统集成和软件开发领域的投标演示。

你的任务是：根据用户提供的投标方案 PPT 内容和项目上下文，生成一份详细的述标讲解方案。

## 输出要求

请严格按照以下 JSON 结构输出，不要包含任何 JSON 之外的文字：

{
  "global_strategy": {
    "opening_approach": "开场切入策略",
    "core_narrative": "核心叙事主线",
    "closing_elevation": "收尾升华方向",
    "total_duration_sec": 1800,
    "key_message": "一句话核心信息"
  },
  "pages": [
    {
      "page_number": 1,
      "importance_level": 3,
      "talking_points": [
        {"point": "要点内容", "is_emphasis": true}
      ],
      "suggested_duration_sec": 120,
      "emphasis_marks": [
        {"text": "需要重音的文字", "reason": "为什么要强调"}
      ],
      "bid_req_mapping": [
        {"req_item": "招标要求项", "coverage": "本页如何覆盖"}
      ],
      "transition_hint": "到下一页的过渡话术"
    }
  ],
  "predicted_questions": [
    {"question": "评委可能问的问题", "answer_direction": "建议回答方向"}
  ],
  "competitive_differentiation": [
    {"vs_competitor": "竞品名", "our_advantage": "我方优势", "talking_script": "建议话术"}
  ],
  "opening_templates": [
    {"style": "稳健型", "script": "..."},
    {"style": "激情型", "script": "..."},
    {"style": "数据型", "script": "..."}
  ],
  "closing_templates": [
    {"style": "稳健型", "script": "..."},
    {"style": "激情型", "script": "..."}
  ]
}

## 注意事项
- importance_level: 1=快速带过 2=重要 3=核心
- 总时长应控制在用户指定的述标时间限制内
- 核心页（importance_level=3）的时间占比应达总时长的 60% 以上
- 讲解要点应具体、可操作，避免空泛表述
- 每页讲解要点 3-5 条"""


def _build_user_prompt(
    customer_industry: str,
    project_name: str,
    project_budget: str,
    bid_time_limit: int,
    bid_requirements: str,
    competitor_info: list,
    pages: list[dict],  # [{page_number, title, content, speaker_notes}]
    knowledge_context: list[dict] | None = None,  # [{content, heading, rrf_score, doc_type}]
) -> str:
    lines = [
        "## 项目信息",
        f"- 客户行业：{customer_industry or '未知'}",
        f"- 项目名称：{project_name}",
        f"- 项目预算：{project_budget or '未知'}",
        f"- 述标时间限制：{bid_time_limit} 分钟",
        "",
        "## 招标要求摘要",
        bid_requirements or "（未提供）",
        "",
    ]

    # Inject top knowledge snippets (capped at 5 to limit prompt size)
    if knowledge_context:
        lines += ["## 知识库参考资料（来自历史标书/案例/产品资料）"]
        lines.append("以下内容摘自企业知识库，请在生成讲解方案时合理引用相关经验和话术：")
        for i, hit in enumerate(knowledge_context[:5], 1):
            heading = hit.get("heading") or ""
            heading_str = f"【{heading}】" if heading else ""
            doc_type = hit.get("doc_type") or ""
            type_str = f"（{doc_type}）" if doc_type else ""
            lines.append(f"\n### 参考片段 {i}{type_str}{heading_str}")
            # Cap each snippet at 300 chars to keep prompt size reasonable
            lines.append(hit.get("content", "")[:300])
        lines.append("")

    if competitor_info:
        lines += ["## 竞品信息"]
        for c in competitor_info:
            name = c.get("name", "")
            strength = c.get("strengths", "")
            weakness = c.get("weaknesses", "")
            lines.append(f"- {name}：优势={strength}，劣势={weakness}")
        lines.append("")

    # Cap at 30 pages to keep prompt within LLM context limits
    MAX_PAGES = 30
    if len(pages) > MAX_PAGES:
        # Keep first 5, last 3, and sample the middle evenly
        head = pages[:5]
        tail = pages[-3:]
        middle_count = MAX_PAGES - len(head) - len(tail)
        step = max(1, (len(pages) - 8) // middle_count)
        middle = pages[5:-3:step][:middle_count]
        pages = head + middle + tail

    lines.append(f"## PPT 内容（共 {len(pages)} 页，已精简）")
    for p in pages:
        lines += [
            f"\n### 第 {p['page_number']} 页",
            f"标题：{p['title']}",
            f"内容：{p['content'][:500]}",
        ]
        if p.get("speaker_notes"):
            lines.append(f"备注：{p['speaker_notes'][:200]}")

    return "\n".join(lines)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def generate_pitch_plan(
    *,
    project_name: str,
    customer_name: str,
    customer_industry: str,
    project_budget: str,
    bid_time_limit: int,
    bid_requirements: str,
    competitor_info: list,
    pages: list[dict],
    person_names: list[str] | None = None,
    knowledge_context: list[dict] | None = None,
    progress_callback=None,
) -> dict:
    """
    Call DeepSeek to generate a structured pitch plan.
    Desensitizes PII before sending; restores it in the response.
    progress_callback(pct: int, stage: str) is called at key points.
    """
    ctx = DesensitizeContext()
    customer_names = [n for n in [customer_name] if n]
    persons = person_names or []

    def _d(text: str) -> str:
        return ctx.desensitize(text, customer_names, persons)

    desensitized_pages = [
        {
            "page_number": p["page_number"],
            "title": _d(p["title"]),
            "content": _d(p["content"]),
            "speaker_notes": _d(p.get("speaker_notes", "")),
        }
        for p in pages
    ]

    user_prompt = _build_user_prompt(
        customer_industry=_d(customer_industry or ""),
        project_name=_d(project_name),
        project_budget=_d(project_budget or ""),
        bid_time_limit=bid_time_limit,
        bid_requirements=_d(bid_requirements or ""),
        competitor_info=competitor_info,
        pages=desensitized_pages,
        knowledge_context=knowledge_context,
    )

    if progress_callback:
        await progress_callback(10, "sending_to_llm")

    response = await _get_client().chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=settings.llm_max_tokens,
        temperature=settings.llm_temperature,
        extra_body={"enable_thinking": False},
    )

    if progress_callback:
        await progress_callback(80, "parsing_response")

    raw = response.choices[0].message.content
    plan = _parse_json_response(raw)

    # Restore desensitized placeholders in string fields
    plan = _restore_plan(plan, ctx)

    if progress_callback:
        await progress_callback(100, "done")

    return plan


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw)


def _restore_plan(plan: dict, ctx: DesensitizeContext) -> dict:
    raw = json.dumps(plan, ensure_ascii=False)
    restored = ctx.restore(raw)
    return json.loads(restored)


_SCRIPT_SYSTEM_PROMPT = """你是一位拥有 15 年经验的专业述标主讲人，擅长将 PPT 要点转化为自然流畅、有感染力的口头讲解话术。

你的任务是：根据每页 PPT 的讲解要点，生成一段适合真实述标场景的口语化讲解脚本。

## 输出要求

严格按照以下 JSON 结构输出，不要包含任何 JSON 之外的文字：

{
  "pages": [
    {
      "page_number": 1,
      "script": "口语化的讲解脚本，自然流畅，适合朗读",
      "duration_estimate_sec": 45,
      "tone": "稳健型"
    }
  ]
}

## 脚本写作规则
- 口语化，像在和人说话，不是在念 PPT
- 每页 50-200 字，根据重要程度和建议时长调整
- 核心页（importance_level=3）内容更充实，次要页简洁带过
- 自然衔接，包含过渡语（"接下来"、"我们看一下"等）
- 避免"第X页"、"如图所示"等演示套话
- 述标语气：专业自信，不卑不亢"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def generate_page_scripts(
    pages: list[dict],  # [{page_number, page_title, talking_points, importance_level, suggested_duration}]
    project_name: str = "",
    bid_time_limit: int = 30,
) -> list[dict]:
    """
    Generate spoken scripts for each plan page via LLM.
    Returns [{page_number, script, duration_estimate_sec, tone}]
    """
    lines = [
        f"## 述标项目：{project_name or '未知项目'}",
        f"## 总时长限制：{bid_time_limit} 分钟",
        "",
        "## 各页讲解要点",
    ]
    for p in pages:
        pts = p.get("talking_points", [])
        pts_text = "\n".join(
            f"  - {'[重点] ' if pt.get('is_emphasis') else ''}{pt.get('point', pt) if isinstance(pt, dict) else pt}"
            for pt in pts
        )
        lines += [
            f"\n### 第 {p['page_number']} 页（{p.get('page_title', '')}）",
            f"重要程度：{p.get('importance_level', 2)}（1=快速带过 2=重要 3=核心）",
            f"建议时长：{p.get('suggested_duration', 60)} 秒",
            f"讲解要点：\n{pts_text}",
        ]

    user_prompt = "\n".join(lines)

    response = await _get_client().chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SCRIPT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
        temperature=0.4,
        extra_body={"enable_thinking": False},
    )

    raw = response.choices[0].message.content
    result = _parse_json_response(raw)
    return result.get("pages", [])
