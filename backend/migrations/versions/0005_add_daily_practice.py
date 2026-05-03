"""P1 F9: add daily_practice_item, daily_practice_log, user_streak tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import json

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- practice content pool ---
    op.create_table(
        "daily_practice_item",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("practice_type", sa.String(32), nullable=False),
        sa.Column("weekday", sa.SmallInteger),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("instruction", sa.Text, nullable=False),
        sa.Column("target_duration_sec", sa.Integer, nullable=False, server_default="60"),
        sa.Column("key_points", sa.JSON),
        sa.Column("reference_answer", sa.Text),
        sa.Column("industry", sa.String(64)),
        sa.Column("source", sa.String(32), nullable=False, server_default="system"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # --- user practice session logs ---
    op.create_table(
        "daily_practice_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("item_id", sa.BigInteger, nullable=False),
        sa.Column("practice_date", sa.Date, nullable=False),
        sa.Column("audio_url", sa.String(512)),
        sa.Column("audio_duration_sec", sa.Integer),
        sa.Column("transcript", sa.Text),
        sa.Column("total_score", sa.Numeric(5, 2)),
        sa.Column("completion_ok", sa.Boolean),
        sa.Column("timing_sec", sa.Integer),
        sa.Column("filler_count", sa.Integer),
        sa.Column("keyword_hit_rate", sa.Numeric(4, 3)),
        sa.Column("feedback", sa.JSON),
        sa.Column("status", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_dp_user_date", "daily_practice_log", ["user_id", "practice_date"])
    op.create_index("idx_dp_tenant", "daily_practice_log", ["tenant_id"])

    # --- streak tracking ---
    op.create_table(
        "user_streak",
        sa.Column("user_id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", sa.BigInteger, nullable=False),
        sa.Column("current_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_practice_date", sa.Date),
        sa.Column("total_practices", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_streak_tenant", "user_streak", ["tenant_id"])

    # --- seed system practice content ---
    _seed_system_items()


def _seed_system_items() -> None:
    """Insert 7 system template practice items (Mon-Sun)."""
    conn = op.get_bind()

    items = [
        # Monday (0) — company intro
        (
            "intro", 0, "公司介绍口播练习",
            "请用 60 秒介绍你的公司：\n1. 公司名称与主营业务\n2. 核心优势或差异化竞争力（1-2 条）\n3. 代表性客户或成功案例（1 条）\n\n提示：语速适中，结尾留 5 秒给评委提问。",
            60,
            json.dumps(["公司名称", "主营业务", "核心优势", "客户案例"], ensure_ascii=False),
            "示例：我们是XX科技，专注于工业互联网领域，核心产品是面向离散制造业的 MES 系统。与同类产品相比，我们的优势在于部署周期短——平均 6 周上线，同时提供7x24小时驻场支持。目前已在汽车零部件行业服务超过 50 家工厂，其中包括XX集团和YY制造。",
        ),
        # Tuesday (1) — case study
        (
            "case", 1, "成功案例讲解练习",
            "请用 90 秒讲述一个你最熟悉的客户成功案例：\n1. 客户背景（行业、规模）\n2. 核心痛点是什么\n3. 你们提供的解决方案\n4. 量化的交付成果（数字、时间、百分比）\n\n提示：用 STAR 结构（情境-任务-行动-结果）让案例更有说服力。",
            90,
            json.dumps(["客户背景", "痛点", "解决方案", "成果", "量化数据"], ensure_ascii=False),
            "示例：某汽车零部件厂商，产线有 200 台设备，原来靠人工巡检，月均故障停机 40 小时。我们部署了设备预测性维护系统，接入 OPC UA 采集实时数据，结合我们的 AI 诊断引擎，提前 3-5 天预警异常。上线 6 个月后，计划外停机减少 72%，节约维修成本约 180 万元/年。",
        ),
        # Wednesday (2) — technical term explanation
        (
            "term", 2, "技术术语口头解释",
            "请用一句话（不超过 30 秒）解释以下技术术语，让非技术背景的评委也能听懂：\n\n「工业互联网平台」\n\n要求：避免堆砌专业词汇，用类比或举例让说明更生动。",
            30,
            json.dumps(["工业互联网", "设备连接", "数据采集", "智能分析"], ensure_ascii=False),
            "工业互联网平台，简单说就是工厂里设备的大脑加神经系统——把各类机器设备连接起来，实时收集它们的运行数据，然后通过 AI 分析，告诉工厂：哪台设备快坏了、哪条产线效率低、哪个环节在浪费能源——帮工厂变得更聪明、更省钱。",
        ),
        # Thursday (3) — Q&A challenge
        (
            "qa", 3, "评委质疑应对练习",
            "模拟评委提问，请在 60 秒内给出有力回答：\n\n评委问题：\n「你们的产品和市面上其他 MES 厂商相比，核心差异在哪里？为什么我们要选你们而不是行业里更知名的厂商？」\n\n提示：先承认竞品优势，再突出自身差异化，最后用数据或案例佐证。",
            60,
            json.dumps(["差异化", "优势", "案例佐证", "客户价值"], ensure_ascii=False),
            "大厂产品确实在品牌认知度上有优势。但我们的核心差异在于三点：第一，部署灵活——我们支持私有化部署，数据不出厂区；第二，响应快——我们在本地有专属实施团队，承诺 4 小时响应；第三，深度定制——专注离散制造业，上线周期比通用产品短 40%。",
        ),
        # Friday (4) — competitive positioning
        (
            "competitive", 4, "竞品差异化话术练习",
            "请用 90 秒完成竞品对比话术：\n\n场景：客户正在对比你们和某知名大厂的产品，询问「如果选你们，和大厂比有什么风险？」\n\n要求：\n1. 正视风险，不要回避\n2. 提出具体的风险缓解措施\n3. 强调选择你们的额外收益\n\n提示：诚实应对反而能建立信任。",
            90,
            json.dumps(["风险承认", "缓解措施", "差异收益", "保障承诺"], ensure_ascii=False),
            "选择我们相比大厂，主要有两个风险需要正视：一是品牌背书相对弱；二是生态资源少一些。我们的应对方案是：第一，提供 3 个月免费试运行期，验收达标后再付款；第二，提供同行业 5 家客户的联系方式供背调；第三，合同里承诺 SLA：系统可用性大于等于 99.5%，否则按比例补偿。这三条，大厂基本做不到。",
        ),
        # Saturday (5) — weekly review
        (
            "review", 5, "本周综合复习",
            "请自选本周最薄弱的一个环节，完整练习 60-90 秒：\n\n可选题目：\n- 公司介绍（重练周一内容）\n- 成功案例讲解（重练周二内容）\n- 评委质疑应答（重练周四内容）\n\n提示：把本周得分最低的维度作为重点练习对象。",
            90,
            json.dumps([], ensure_ascii=False),
            None,
        ),
        # Sunday (6) — full simulation
        (
            "review", 6, "述标场景模拟",
            "模拟完整述标开场 90 秒：\n\n请用 90 秒完成述标开场白，包含：\n1. 自我介绍（10 秒）\n2. 公司简介（20 秒）\n3. 本次方案核心亮点预告（30 秒）\n4. 述标议程概述（15 秒）\n5. 过渡语（5 秒）\n\n提示：开场要自信、清晰，为整场述标定调。",
            90,
            json.dumps(["自我介绍", "公司简介", "方案亮点", "议程", "过渡语"], ensure_ascii=False),
            "各位评委好，我是XX科技的解决方案总监张三，感谢XX集团给我们这次述标机会。XX科技成立于2015年，专注于离散制造业数字化，目前已服务 300 余家制造企业。今天的方案有三个亮点：第一，6周极速上线；第二，基于现有系统无缝集成；第三，ROI 周期 18 个月。接下来用约 25 分钟，依次介绍需求理解、方案设计、实施计划和服务保障。有任何问题随时打断，欢迎互动式述标。",
        ),
    ]

    for (ptype, weekday, title, instruction, duration, key_points, ref_answer) in items:
        conn.execute(
            sa.text(
                "INSERT INTO daily_practice_item "
                "(practice_type, weekday, title, instruction, target_duration_sec, "
                "key_points, reference_answer, industry, source, is_active) "
                "VALUES (:practice_type, :weekday, :title, :instruction, :target_duration_sec, "
                ":key_points, :reference_answer, :industry, :source, :is_active)"
            ),
            {
                "practice_type": ptype,
                "weekday": weekday,
                "title": title,
                "instruction": instruction,
                "target_duration_sec": duration,
                "key_points": key_points,
                "reference_answer": ref_answer,
                "industry": None,
                "source": "system",
                "is_active": True,
            },
        )


def downgrade() -> None:
    op.drop_index("idx_streak_tenant", "user_streak")
    op.drop_table("user_streak")
    op.drop_index("idx_dp_tenant", "daily_practice_log")
    op.drop_index("idx_dp_user_date", "daily_practice_log")
    op.drop_table("daily_practice_log")
    op.drop_table("daily_practice_item")
