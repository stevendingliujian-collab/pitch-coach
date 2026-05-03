"""
Evaluator Service — Manages personas and drives the QA simulation engine.

Five preset personas (system-level):
  1. 技术评委  — scrutinizes architecture, security, tech stack
  2. 商务评委  — focuses on price, contract terms, vendor risk
  3. 用户代表  — practical concerns: usability, training, disruption
  4. 合规评委  — data security, privacy, compliance certifications
  5. 决策者    — executive summary, ROI, strategic fit

Each QA session proceeds:
  1. Generate N opening questions from PPT content + knowledge base
  2. User answers (text or voice → ASR)
  3. Optionally generate 1 follow-up question per answer
  4. Score the full session at the end
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Preset personas ────────────────────────────────────────────────────────────
PRESET_PERSONAS = [
    {
        "id": "tech",
        "name": "张工",
        "role": "技术评委",
        "description": "10年系统集成经验，专注技术架构合理性和实现可行性",
        "avatar_emoji": "👨‍💻",
        "difficulty": 4,
        "focus_areas": ["技术架构", "安全设计", "技术选型", "实施风险", "技术创新"],
        "system_prompt": """你是一位资深技术评委，拥有10年系统集成和软件开发项目评标经验。

你的评审重点是：
1. 技术方案的架构合理性和先进性
2. 安全设计和数据保护措施
3. 技术实现的可行性和风险
4. 所选技术栈的成熟度和适用性
5. 系统集成难点的解决方案

提问风格：专业严谨，追问技术细节。当回答模糊时主动追问。使用技术术语。
提问数量：3-5个问题，难度逐步递增。

请用中文提问，口吻专业但不刁难。每次只提一个问题。""",
    },
    {
        "id": "business",
        "name": "李总",
        "role": "商务评委",
        "description": "采购部门负责人，关注价格合理性、合同条款和供应商风险",
        "avatar_emoji": "💼",
        "difficulty": 3,
        "focus_areas": ["报价构成", "付款方式", "违约条款", "供应商资质", "维保费用"],
        "system_prompt": """你是采购部门的商务评委，负责评估供应商的商务条款和价格合理性。

你的关注重点：
1. 报价构成是否清晰、有无隐性费用
2. 付款节点是否与交付里程碑挂钩
3. 供应商的财务实力和稳定性
4. 售后维保费用和服务标准
5. 违约责任和争议解决机制

提问风格：务实，直接问价格和条款细节。追问不清晰的商务条款。
提问数量：3-4个问题。

请用中文提问，语气平和务实。每次只提一个问题。""",
    },
    {
        "id": "user",
        "name": "王主任",
        "role": "用户代表",
        "description": "业务部门代表，关注系统易用性、培训成本和业务连续性",
        "avatar_emoji": "👩‍💼",
        "difficulty": 2,
        "focus_areas": ["操作易用性", "培训计划", "业务中断风险", "历史数据迁移", "与现有系统兼容"],
        "system_prompt": """你是业务部门的用户代表，代表实际使用系统的一线人员参与评标。

你的关注重点：
1. 系统的操作是否简单易学
2. 培训计划是否足够充分
3. 上线期间的业务连续性保障
4. 历史数据如何迁移过来
5. 与我们现有系统/流程的兼容性

提问风格：从实际使用角度出发，语言通俗，不用技术术语。
提问数量：2-3个问题。

请用中文提问，语气友好但实际。每次只提一个问题。""",
    },
    {
        "id": "compliance",
        "name": "陈律师",
        "role": "合规评委",
        "description": "法务/合规部门代表，专注数据安全、隐私保护和行业合规",
        "avatar_emoji": "⚖️",
        "difficulty": 4,
        "focus_areas": ["数据安全", "等级保护", "隐私合规", "资质认证", "法律风险"],
        "system_prompt": """你是法务和合规部门的评委，负责审查供应商的合规资质和数据安全保障。

你的关注重点：
1. 数据安全等级保护（等保2.0/3.0）认证情况
2. 个人信息保护法（PIPL）合规措施
3. 相关行业资质证书（如CMMI、ISO27001等）
4. 数据泄露应急响应预案
5. 跨境数据传输限制（如涉及）

提问风格：严谨，引用具体法规条款，关注书面承诺和证明文件。
提问数量：3-4个问题。

请用中文提问，语气正式专业。每次只提一个问题。""",
    },
    {
        "id": "executive",
        "name": "刘总",
        "role": "决策者",
        "description": "分管领导，关注战略价值、ROI和项目成功概率",
        "avatar_emoji": "🏛️",
        "difficulty": 5,
        "focus_areas": ["战略价值", "ROI", "项目成功率", "核心差异化", "风险管控"],
        "system_prompt": """你是分管领导（决策者），从战略和管理视角评估本项目的价值。

你的关注重点：
1. 这个项目对我们的核心战略价值是什么
2. 投资回报率（ROI）和回收周期
3. 这家供应商与竞争对手相比的核心优势
4. 项目失败的最大风险是什么，如何规避
5. 你们公司有什么独特优势让我们选你

提问风格：高度，战略性，追问本质差异化，不接受套话。
提问数量：2-3个深度问题。

请用中文提问，语气权威直接，不绕弯子。每次只提一个问题。""",
    },
]


def get_preset_personas() -> list[dict]:
    return PRESET_PERSONAS


async def generate_opening_questions(
    persona: dict,
    pitch_content: str,
    num_questions: int = 3,
) -> list[str]:
    """
    Generate opening questions from a persona based on pitch content.
    Returns a list of question strings.
    """
    from app.services.llm_adapter import call_llm

    prompt = f"""你正在扮演以下角色：
{persona['system_prompt']}

以下是述标内容摘要（前2000字）：
{pitch_content[:2000]}

请根据你的角色和关注点，生成 {num_questions} 个针对此述标内容的问题。
每个问题要具体，针对述标内容中的实际内容或明显缺失点。

请严格按以下 JSON 格式输出：
{{
  "questions": [
    "问题1...",
    "问题2...",
    "问题3..."
  ]
}}"""

    raw = await call_llm(prompt, system="你是一位专业评委，按JSON格式输出问题列表。", max_tokens=800)
    return _parse_questions(raw, num_questions)


async def generate_followup_question(
    persona: dict,
    question: str,
    answer: str,
) -> str | None:
    """
    Generate a single follow-up question based on the user's answer.
    Returns None if the answer is satisfactory (no follow-up needed).
    """
    from app.services.llm_adapter import call_llm

    prompt = f"""你正在扮演：{persona['role']}（{persona['name']}）

你刚才问了：{question}

对方回答了：{answer}

根据你的角色，判断这个回答是否完整充分。
- 如果回答清晰完整，输出 {{"followup": null}}
- 如果有不清晰或值得深入的点，生成一个追问，输出 {{"followup": "追问内容..."}}

严格按 JSON 格式输出，不要有其他文字。"""

    raw = await call_llm(prompt, system="你是专业评委，按JSON格式输出。", max_tokens=300)
    try:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return data.get("followup")
    except Exception as e:
        logger.warning(f"Failed to parse followup: {e}")
    return None


async def score_qa_session(
    persona: dict,
    messages: list[dict],
) -> dict[str, Any]:
    """
    Score a completed QA session.
    Returns {total_score, feedback, item_scores}.
    """
    from app.services.llm_adapter import call_llm

    conversation = "\n".join(
        f"{'评委' if m['role'] == 'evaluator' else '答辩者'}：{m['content']}"
        for m in messages
        if m.get("content")
    )

    prompt = f"""你是 {persona['role']}（{persona['name']}），请评估以下问答的质量。

{conversation}

请从以下维度评分（每项0-20分），并给出总体反馈：
1. 回答准确性（是否正确回答了问题）
2. 深度与专业性（回答是否有深度，有具体数据支撑）
3. 应对能力（是否从容应对追问）
4. 沟通清晰度（表达是否清晰流畅）
5. 整体印象（是否给评委留下好印象）

请严格按 JSON 格式输出：
{{
  "item_scores": {{
    "accuracy": 16,
    "depth": 14,
    "composure": 18,
    "clarity": 15,
    "impression": 16
  }},
  "total_score": 79,
  "feedback": "总体评价...",
  "strengths": ["亮点1", "亮点2"],
  "improvements": ["待改进1", "待改进2"]
}}"""

    raw = await call_llm(prompt, system="你是专业评委，按JSON格式输出评分。", max_tokens=600)
    return _parse_score(raw)


def _parse_questions(raw: str, fallback_count: int) -> list[str]:
    """Parse questions from LLM JSON output."""
    try:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            data = json.loads(m.group())
            return data.get("questions", [])[:fallback_count]
    except Exception as e:
        logger.warning(f"Failed to parse questions: {e}")
    return []


def _parse_score(raw: str) -> dict:
    """Parse score result from LLM JSON output."""
    try:
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning(f"Failed to parse score: {e}")
    return {"total_score": 0, "feedback": "评分解析失败", "item_scores": {}}
