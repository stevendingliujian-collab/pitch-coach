"""
F7 AI 复盘助手 — 对真实述标会议录音进行自动分析

流程：
1. 上传录音 → MinIO → 触发 Celery 任务
2. Celery 任务：
   a. ASR 转录（Paraformer → transcript_json）
   b. 说话人分离（基于 LLM 推断，区分我方 vs 评委）
   c. 评委问题提取 + 分类（技术/商务/用户/合规/其他）
   d. 与排练预测对比（命中率）
   e. 回答质量评估（对比知识库标准答案）
   f. 答疑函草拟
   g. 关键时刻提取
   h. 整体洞察生成
"""
from __future__ import annotations

import json
from typing import Any

from app.services.llm_adapter import call_llm


# ─── 1. 说话人分离 ────────────────────────────────────────────────────────────

async def diarize_transcript(transcript_text: str) -> dict:
    """
    将 ASR 转录文本进行说话人分离。
    由于没有音频特征，使用 LLM 基于语义推断说话人角色。
    返回：{segments: [{speaker, text, inferred_role}], our_talk_ratio, evaluator_count}
    """
    prompt = f"""你是述标会议分析专家。以下是一段述标会议的语音转录文本（未区分说话人）。

请分析对话内容，将其拆分为"我方陈述者"和"评委"两类说话人。
- 我方陈述者：介绍产品/方案/公司，回答问题的一方
- 评委：提问、质疑、要求说明的一方（可能有多位）

会议录音转录：
{transcript_text[:3000]}

请按 JSON 格式返回分析结果：
{{
  "segments": [
    {{
      "speaker": "我方" | "评委_1" | "评委_2" | ...,
      "text": "该段原文",
      "inferred_role": "presenter" | "evaluator"
    }}
  ],
  "our_talk_ratio": 0.65,
  "evaluator_count": 3,
  "summary": "对话整体描述（1-2句）"
}}

只返回 JSON，不要其他内容。"""

    result = await call_llm(prompt, system="你是述标会议分析专家，擅长识别说话人和对话结构。")
    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        # Fallback: treat entire text as ours
        data = {
            "segments": [{"speaker": "我方", "text": transcript_text, "inferred_role": "presenter"}],
            "our_talk_ratio": 0.8,
            "evaluator_count": 1,
            "summary": "无法解析说话人结构"
        }
    return data


# ─── 2. 评委问题提取 ─────────────────────────────────────────────────────────

QUESTION_CATEGORIES = {
    "tech": "技术类",
    "business": "商务类",
    "user": "用户/运维类",
    "compliance": "合规/资质类",
    "other": "其他"
}


async def extract_evaluator_questions(segments: list[dict]) -> list[dict]:
    """
    从说话人分离结果中提取评委问题，并分类。
    返回：[{id, category, question, answer_text, answer_quality, notes}]
    """
    # Build evaluator segments only
    evaluator_texts = []
    for i, seg in enumerate(segments):
        if seg.get("inferred_role") == "evaluator":
            evaluator_texts.append(f"[{i}] {seg['speaker']}: {seg['text']}")

    if not evaluator_texts:
        return []

    combined = "\n".join(evaluator_texts[:50])  # Limit to 50 segments

    # Also collect answers (our side following each evaluator question)
    qa_context = []
    for i, seg in enumerate(segments):
        if seg.get("inferred_role") == "evaluator":
            # Find the next presenter segment as answer
            answer = ""
            for j in range(i + 1, min(i + 3, len(segments))):
                if segments[j].get("inferred_role") == "presenter":
                    answer = segments[j]["text"]
                    break
            qa_context.append({
                "question": seg["text"],
                "answer": answer
            })

    qa_json = json.dumps(qa_context[:20], ensure_ascii=False, indent=2)

    prompt = f"""你是述标评委问题分析专家。以下是述标会议中评委提出的问题及我方回答：

{qa_json}

请对每个问题进行分析，返回 JSON 数组：
[
  {{
    "id": 1,
    "category": "tech" | "business" | "user" | "compliance" | "other",
    "category_name": "技术类",
    "question": "评委原始问题",
    "answer_text": "我方回答原文",
    "answer_quality": 1-5整数（5=完美，4=良好，3=一般，2=较差，1=未回答），
    "question_type": "clarification" | "challenge" | "requirement" | "concern",
    "notes": "分析评语（1句话）",
    "is_risky": true/false（是否是高风险/挑剔问题）
  }}
]

只返回 JSON 数组，不要其他内容。"""

    result = await call_llm(prompt, system="你是述标评委问题分析专家。")
    try:
        questions = json.loads(result.strip())
        if not isinstance(questions, list):
            questions = []
    except json.JSONDecodeError:
        questions = []

    return questions


# ─── 3. 预测命中率 ────────────────────────────────────────────────────────────

async def calculate_prediction_hit_rate(
    actual_questions: list[dict],
    predicted_questions: list[str]
) -> dict:
    """
    对比实际评委问题 vs 排练时预测的问题，计算命中率。
    返回：{hit_rate, matched, missed, unexpected}
    """
    if not predicted_questions or not actual_questions:
        return {"hit_rate": 0.0, "matched": [], "missed": predicted_questions or [], "unexpected": []}

    actual_q_texts = [q.get("question", "") for q in actual_questions]
    pred_str = "\n".join(f"- {q}" for q in predicted_questions[:20])
    actual_str = "\n".join(f"- {q}" for q in actual_q_texts[:20])

    prompt = f"""比较以下两组问题，判断预测问题与实际问题的命中情况：

预测的评委问题（排练时预测）：
{pred_str}

实际评委问题（会议录音提取）：
{actual_str}

判断标准：语义相似即为命中（不需要完全一致，意思相近即可）

返回 JSON：
{{
  "hit_rate": 0.0-1.0的小数,
  "matched": ["被命中的预测问题列表"],
  "missed": ["未命中的预测问题（评委实际问但没预测到）"],
  "unexpected": ["预测到但实际未问的问题"]
}}

只返回 JSON，不要其他内容。"""

    result = await call_llm(prompt, system="你是述标复盘分析专家。")
    try:
        data = json.loads(result.strip())
    except json.JSONDecodeError:
        data = {"hit_rate": 0.0, "matched": [], "missed": actual_q_texts, "unexpected": predicted_questions}
    return data


# ─── 4. 回答质量评估（结合知识库） ────────────────────────────────────────────

async def assess_answers(
    questions: list[dict],
    kb_context: str = ""
) -> list[dict]:
    """
    对每个评委问题的回答进行深度评估，结合知识库标准答案。
    返回：[{question_id, score, feedback, suggestion, reference_from_kb}]
    """
    if not questions:
        return []

    # Only assess questions with answers and low quality
    to_assess = [q for q in questions if q.get("answer_text") and q.get("answer_quality", 5) <= 3]
    if not to_assess:
        to_assess = questions[:5]  # Assess top 5 anyway

    qa_json = json.dumps([{
        "id": q.get("id"),
        "category": q.get("category_name", ""),
        "question": q.get("question", ""),
        "answer": q.get("answer_text", ""),
        "quality": q.get("answer_quality", 3)
    } for q in to_assess], ensure_ascii=False, indent=2)

    kb_section = f"\n\n知识库参考内容：\n{kb_context[:1500]}" if kb_context else ""

    prompt = f"""你是述标回答质量评估专家。请对以下问答进行深度评估：

{qa_json}{kb_section}

对每个问题返回改进建议，格式为 JSON 数组：
[
  {{
    "question_id": 1,
    "score": 1-5整数,
    "feedback": "回答评价（1-2句）",
    "suggestion": "改进建议（具体可操作，1-3句）",
    "reference_from_kb": "如有知识库参考，引用相关内容",
    "ideal_answer_outline": "理想回答要点（2-3点）"
  }}
]

只返回 JSON 数组。"""

    result = await call_llm(prompt, system="你是述标回答质量评估专家。")
    try:
        assessments = json.loads(result.strip())
        if not isinstance(assessments, list):
            assessments = []
    except json.JSONDecodeError:
        assessments = []
    return assessments


# ─── 5. 答疑函草拟 ────────────────────────────────────────────────────────────

async def draft_followup_letter(
    task_name: str,
    customer_name: str,
    questions: list[dict],
    assessments: list[dict],
    kb_context: str = ""
) -> str:
    """
    基于评委问题和知识库，草拟述标后的答疑跟进函。
    """
    # Select unanswered or poorly answered questions
    problem_qs = [q for q in questions if q.get("answer_quality", 5) <= 3]
    if not problem_qs:
        problem_qs = questions[:3]

    q_summary = "\n".join(
        f"{i+1}. [{q.get('category_name','')}] {q.get('question','')}"
        for i, q in enumerate(problem_qs[:8])
    )

    assessment_map = {a.get("question_id"): a for a in (assessments or [])}

    prompt = f"""你是述标专家，请为以下述标项目草拟一份答疑跟进函。

项目名称：{task_name}
客户名称：{customer_name or "客户"}

会议中评委提出的主要问题（需要跟进答复）：
{q_summary}

知识库补充内容：
{kb_context[:1000] if kb_context else "（无）"}

要求：
1. 商务信函格式，专业规范
2. 开头感谢客户时间，表达诚意
3. 对每个问题给出书面补充说明（要点式，不超过3点/问题）
4. 结尾表达配合意愿，附上联系方式占位符
5. 中文，500-800字

直接输出信函正文，不要额外说明。"""

    letter = await call_llm(prompt, system="你是专业的商务写作专家，擅长IT项目的述标跟进函。", max_tokens=1500)
    return letter.strip()


# ─── 6. 关键时刻提取 ──────────────────────────────────────────────────────────

async def extract_key_moments(segments: list[dict]) -> list[dict]:
    """
    从对话段落中提取关键时刻（精彩回答、高压时刻、关键决策点）。
    """
    if not segments:
        return []

    sample = json.dumps(segments[:30], ensure_ascii=False, indent=2)

    prompt = f"""分析以下述标会议对话，提取关键时刻：

{sample}

关键时刻类型：
- highlight: 精彩回答（得分点）
- pressure: 高压质疑（需要特别应对的挑战）
- turning_point: 转折点（评委态度明显变化）
- missed: 错失机会（可以更好回答但没有抓住）

返回 JSON 数组：
[
  {{
    "type": "highlight" | "pressure" | "turning_point" | "missed",
    "speaker": "说话人",
    "text": "原文（最多100字）",
    "analysis": "分析（1句话）",
    "importance": 1-5
  }}
]

最多返回8个关键时刻。只返回 JSON 数组。"""

    result = await call_llm(prompt, system="你是述标复盘分析专家。")
    try:
        moments = json.loads(result.strip())
        if not isinstance(moments, list):
            moments = []
    except json.JSONDecodeError:
        moments = []
    return moments


# ─── 7. 综合洞察生成 ──────────────────────────────────────────────────────────

async def generate_insights(
    task_name: str,
    questions: list[dict],
    answer_assessments: list[dict],
    our_talk_ratio: float,
    prediction_hit_rate: float,
) -> dict:
    """
    生成述标复盘的整体洞察报告。
    """
    q_categories = {}
    for q in questions:
        cat = q.get("category", "other")
        q_categories[cat] = q_categories.get(cat, 0) + 1

    avg_answer_quality = (
        sum(q.get("answer_quality", 3) for q in questions) / len(questions)
        if questions else 3
    )

    prompt = f"""基于以下述标复盘数据，生成整体洞察报告：

项目：{task_name}
我方发言占比：{our_talk_ratio:.0%}
评委问题数量：{len(questions)}
问题分类：{json.dumps(q_categories, ensure_ascii=False)}
预测命中率：{prediction_hit_rate:.0%}
平均回答质量：{avg_answer_quality:.1f}/5

返回 JSON：
{{
  "overall_score": 1-100整数（述标表现综合评分）,
  "grade": "优秀" | "良好" | "一般" | "待改进",
  "strengths": ["优势点1", "优势点2", "优势点3"],
  "weaknesses": ["不足1", "不足2", "不足3"],
  "top_risks": ["最高风险项（可能影响中标的因素）"],
  "action_items": [
    {{"priority": "high" | "medium", "action": "具体行动建议", "deadline": "建议时间"}}
  ],
  "prediction_summary": "预测准确性评价（1句）",
  "next_rehearsal_focus": ["下次排练重点关注的方向"]
}}

只返回 JSON。"""

    result = await call_llm(prompt, system="你是资深述标复盘顾问。")
    try:
        insights = json.loads(result.strip())
    except json.JSONDecodeError:
        insights = {
            "overall_score": 70,
            "grade": "良好",
            "strengths": ["完成了完整的述标陈述"],
            "weaknesses": ["需要进一步分析"],
            "top_risks": [],
            "action_items": [],
            "prediction_summary": "复盘分析完成",
            "next_rehearsal_focus": ["加强问答环节准备"]
        }
    return insights


# ─── 8. 完整复盘流程（供 Celery 任务调用） ────────────────────────────────────

async def run_full_post_mortem(
    transcript_text: str,
    task_name: str,
    customer_name: str = "",
    predicted_questions: list[str] | None = None,
    kb_context: str = "",
) -> dict:
    """
    执行完整复盘分析流程，返回所有分析结果。
    """
    predicted_questions = predicted_questions or []

    # Step 1: 说话人分离
    diarization_result = await diarize_transcript(transcript_text)
    segments = diarization_result.get("segments", [])
    our_talk_ratio = float(diarization_result.get("our_talk_ratio", 0.7))
    evaluator_count = int(diarization_result.get("evaluator_count", 1))

    # Step 2: 评委问题提取
    questions = await extract_evaluator_questions(segments)
    question_count = len(questions)

    # Step 3: 问题分类汇总
    categories: dict[str, int] = {}
    for q in questions:
        cat = q.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    # Step 4: 预测命中率
    hit_result = await calculate_prediction_hit_rate(questions, predicted_questions)
    prediction_hit_rate = float(hit_result.get("hit_rate", 0.0))

    # Step 5: 回答质量评估
    assessments = await assess_answers(questions, kb_context)

    # Step 6: 答疑函草拟
    followup = await draft_followup_letter(task_name, customer_name, questions, assessments, kb_context)

    # Step 7: 关键时刻
    key_moments = await extract_key_moments(segments)

    # Step 8: 综合洞察
    insights = await generate_insights(
        task_name, questions, assessments, our_talk_ratio, prediction_hit_rate
    )

    return {
        "diarization": segments,
        "evaluator_questions": questions,
        "our_talk_ratio": our_talk_ratio,
        "evaluator_count": evaluator_count,
        "question_count": question_count,
        "question_categories": categories,
        "prediction_hit_rate": prediction_hit_rate,
        "answer_assessments": assessments,
        "followup_draft": followup,
        "key_moments": key_moments,
        "insights": insights,
    }
