"""
Rubric Engine — scoring rubric management and LLM-based rehearsal coverage scoring.

Rubric item structure:
  {
    "id": "1",
    "category": "技术方案",
    "item": "技术架构清晰度",
    "max_score": 10,
    "weight": 0.15,
    "description": "评委会检验..."
  }

Coverage result per item:
  {
    "item_id": "1",
    "score": 8,
    "coverage": true,
    "note": "演讲者明确介绍了...",
    "suggest_page": 3
  }
"""
from __future__ import annotations

import json
import re
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

# ── Preset rubric templates ────────────────────────────────────────────────────
PRESET_TEMPLATES: list[dict] = [
    {
        "template_type": "system_integration",
        "name": "系统集成行业标准评分表",
        "industry": "系统集成",
        "description": "适用于政企系统集成项目的招标述标评分，包含技术、商务、服务、团队四大维度",
        "items": [
            {"id": "1", "category": "技术方案", "item": "技术架构清晰性", "max_score": 15, "weight": 0.15, "description": "技术方案架构描述是否清晰，层次分明"},
            {"id": "2", "category": "技术方案", "item": "需求理解深度", "max_score": 10, "weight": 0.10, "description": "是否充分理解招标方的业务需求和痛点"},
            {"id": "3", "category": "技术方案", "item": "创新性与差异化", "max_score": 10, "weight": 0.10, "description": "方案是否有创新亮点，与竞争对手的差异化"},
            {"id": "4", "category": "实施能力", "item": "项目实施计划", "max_score": 10, "weight": 0.10, "description": "里程碑计划、资源投入、风险管控是否完整"},
            {"id": "5", "category": "实施能力", "item": "成功案例展示", "max_score": 10, "weight": 0.10, "description": "相关行业成功案例的说服力"},
            {"id": "6", "category": "服务保障", "item": "运维支持方案", "max_score": 10, "weight": 0.10, "description": "售后运维、响应时效、SLA承诺"},
            {"id": "7", "category": "服务保障", "item": "培训方案", "max_score": 5, "weight": 0.05, "description": "用户培训计划的完整性和可操作性"},
            {"id": "8", "category": "商务条件", "item": "报价合理性", "max_score": 15, "weight": 0.15, "description": "价格构成清晰，性价比突出"},
            {"id": "9", "category": "团队实力", "item": "团队资质与经验", "max_score": 10, "weight": 0.10, "description": "项目团队的专业资质和行业经验"},
            {"id": "10", "category": "团队实力", "item": "演示汇报质量", "max_score": 5, "weight": 0.05, "description": "述标表达流畅性、逻辑性和感染力"},
        ],
        "total_max_score": 100,
    },
    {
        "template_type": "software_dev",
        "name": "软件开发项目评分表",
        "industry": "软件开发",
        "description": "适用于政府/企业定制软件开发项目招标，重视技术路线和交付保障",
        "items": [
            {"id": "1", "category": "技术方案", "item": "技术路线选型", "max_score": 15, "weight": 0.15, "description": "技术栈选型是否合理，是否有详细说明"},
            {"id": "2", "category": "技术方案", "item": "功能覆盖完整性", "max_score": 15, "weight": 0.15, "description": "是否覆盖招标文件的全部功能需求"},
            {"id": "3", "category": "技术方案", "item": "安全合规设计", "max_score": 10, "weight": 0.10, "description": "数据安全、隐私保护、等保合规方案"},
            {"id": "4", "category": "项目管理", "item": "开发计划与里程碑", "max_score": 10, "weight": 0.10, "description": "交付计划的合理性和可操作性"},
            {"id": "5", "category": "项目管理", "item": "质量保障体系", "max_score": 10, "weight": 0.10, "description": "测试方案、验收标准、缺陷处理流程"},
            {"id": "6", "category": "成功案例", "item": "同类项目经验", "max_score": 15, "weight": 0.15, "description": "同类软件项目案例展示，注重用户评价"},
            {"id": "7", "category": "服务保障", "item": "维保与升级方案", "max_score": 10, "weight": 0.10, "description": "质保期、维保费用、版本升级策略"},
            {"id": "8", "category": "商务", "item": "报价与支付方式", "max_score": 10, "weight": 0.10, "description": "费用构成、分期支付节点的合理性"},
            {"id": "9", "category": "团队", "item": "核心团队介绍", "max_score": 5, "weight": 0.05, "description": "项目经理及核心开发成员的资质"},
        ],
        "total_max_score": 100,
    },
    {
        "template_type": "automation",
        "name": "非标自动化设备评分表",
        "industry": "非标自动化",
        "description": "适用于非标定制自动化设备、智能制造产线的采购评标",
        "items": [
            {"id": "1", "category": "技术方案", "item": "工艺方案合理性", "max_score": 20, "weight": 0.20, "description": "工艺路线设计是否合理，满足产能要求"},
            {"id": "2", "category": "技术方案", "item": "设备选型说明", "max_score": 10, "weight": 0.10, "description": "核心设备品牌、型号、参数的合理性"},
            {"id": "3", "category": "技术方案", "item": "安全设计", "max_score": 10, "weight": 0.10, "description": "安全防护、紧急停车、安规符合性"},
            {"id": "4", "category": "交付保障", "item": "交期承诺", "max_score": 10, "weight": 0.10, "description": "设备交付时间是否符合要求，有无保障措施"},
            {"id": "5", "category": "交付保障", "item": "调试与验收方案", "max_score": 10, "weight": 0.10, "description": "FAT/SAT测试方案，验收标准清晰"},
            {"id": "6", "category": "成功案例", "item": "同类设备案例", "max_score": 15, "weight": 0.15, "description": "相似工艺/行业的成功交付案例"},
            {"id": "7", "category": "服务保障", "item": "售后服务网络", "max_score": 10, "weight": 0.10, "description": "就近服务站、响应时间、备件库存"},
            {"id": "8", "category": "商务", "item": "价格竞争力", "max_score": 15, "weight": 0.15, "description": "报价合理性，含税含运费含安装调试"},
        ],
        "total_max_score": 100,
    },
]


def get_preset_templates() -> list[dict]:
    """Return list of preset template definitions (no DB)."""
    return PRESET_TEMPLATES


def compute_rubric_total(items: list[dict]) -> float:
    """Sum max_score across all items."""
    return sum(float(item.get("max_score", 0)) for item in items)


async def score_rehearsal_against_rubric(
    rubric_items: list[dict],
    transcript: str,
    page_contents: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Use LLM to score a rehearsal transcript against a rubric.

    Returns a dict with keys:
        scores: list[{item_id, score, coverage, note, suggest_page}]
        total_score: float
        coverage_percent: float  (0.0 – 1.0)
        coverage_detail: list[{item_id, covered, evidence}]
        improvement_suggestions: list[{item_id, suggestion}]
    """
    from app.services.llm_adapter import call_llm

    rubric_json = json.dumps(rubric_items, ensure_ascii=False, indent=2)
    page_ctx = ""
    if page_contents:
        pages_summary = []
        for p in page_contents[:20]:  # cap at 20 pages
            pages_summary.append(f"第{p.get('page_number', '?')}页: {p.get('title', '')} — {p.get('summary', '')}")
        page_ctx = "\n\n【PPT各页摘要】\n" + "\n".join(pages_summary)

    prompt = f"""你是一位专业评委，请根据以下评分表对述标录音转录文字进行评分和覆盖度分析。

【评分表】
{rubric_json}

【述标转录文字】
{transcript[:4000]}
{page_ctx}

请严格按以下 JSON 格式输出，不要包含任何 JSON 之外的文字：

{{
  "scores": [
    {{
      "item_id": "1",
      "score": 8,
      "coverage": true,
      "note": "演讲者明确介绍了系统架构图，逻辑清晰",
      "suggest_page": 3
    }}
  ],
  "overall_comments": "总体评价...",
  "improvement_suggestions": [
    {{
      "item_id": "2",
      "suggestion": "建议在讲解需求理解时引用招标文件第X条，并举具体痛点案例"
    }}
  ]
}}

规则：
- 每个评分项都要评分，score 不超过 max_score
- coverage=true 表示演讲者有覆盖该评分点，false 表示未覆盖
- suggest_page 填写最相关的PPT页码（如无法判断填 null）
- 未覆盖的评分项 score 给 0-30% 的分数
- note 要具体，指出哪些话体现了/未体现该评分点"""

    raw = await call_llm(prompt, system="你是专业的述标评委助理，严格按 JSON 格式输出。", max_tokens=2000)
    result = _parse_llm_json(raw)

    # Compute totals
    scores = result.get("scores", [])
    item_map = {str(item["id"]): item for item in rubric_items}
    total_score = 0.0
    covered = 0
    coverage_detail = []

    for s in scores:
        item_id = str(s.get("item_id", ""))
        item = item_map.get(item_id, {})
        max_score = float(item.get("max_score", 10))
        raw_score = float(s.get("score", 0))
        # Clamp to max_score
        s["score"] = min(raw_score, max_score)
        total_score += s["score"]
        is_covered = bool(s.get("coverage", False))
        if is_covered:
            covered += 1
        coverage_detail.append({
            "item_id": item_id,
            "covered": is_covered,
            "evidence": s.get("note", ""),
        })

    total_max = compute_rubric_total(rubric_items) or 100
    coverage_percent = covered / len(scores) if scores else 0.0

    return {
        "scores": scores,
        "total_score": round(total_score, 2),
        "coverage_percent": round(coverage_percent, 3),
        "coverage_detail": coverage_detail,
        "improvement_suggestions": result.get("improvement_suggestions", []),
        "overall_comments": result.get("overall_comments", ""),
        "total_max_score": total_max,
    }


def _parse_llm_json(raw: str) -> dict:
    """Extract and parse the first JSON object from LLM output."""
    try:
        # Strip markdown fences
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        # Find first {...} block
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        logger.warning(f"Failed to parse rubric LLM JSON: {e}")
    return {"scores": [], "improvement_suggestions": []}
