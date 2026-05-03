"""extend pc_user for multi-login support

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── WeChat ───────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("wechat_unionid", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column("wechat_openid_web", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column("wechat_openid_mp", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column("wechat_openid_oa", sa.String(64), nullable=True))
    # ── 企业微信 ─────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("wecom_userid", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column("wecom_corpid", sa.String(64), nullable=True))
    # ── 飞书 ─────────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("feishu_userid", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column("feishu_tenant_key", sa.String(64), nullable=True))
    # ── 钉钉（P2） ────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("dingtalk_userid", sa.String(64), nullable=True))
    # ── CRM SSO ──────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("crm_user_id", sa.String(128), nullable=True))
    # ── 渐进收集 ─────────────────────────────────────────────────────────────
    op.add_column("pc_user", sa.Column("industry", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column(
        "register_source", sa.String(32), nullable=False, server_default="web"
    ))
    op.add_column("pc_user", sa.Column("register_channel", sa.String(64), nullable=True))
    op.add_column("pc_user", sa.Column(
        "profile_completeness", sa.SmallInteger(), nullable=False, server_default="10"
    ))
    op.add_column("pc_user", sa.Column("last_login_source", sa.String(32), nullable=True))

    # ── 唯一索引 ──────────────────────────────────────────────────────────────
    op.create_index("uk_wechat_unionid", "pc_user", ["wechat_unionid"], unique=True,
                    postgresql_where=sa.text("wechat_unionid IS NOT NULL"))
    op.create_index("uk_wecom", "pc_user", ["wecom_corpid", "wecom_userid"], unique=True,
                    postgresql_where=sa.text("wecom_userid IS NOT NULL"))
    op.create_index("uk_feishu", "pc_user", ["feishu_tenant_key", "feishu_userid"], unique=True,
                    postgresql_where=sa.text("feishu_userid IS NOT NULL"))
    op.create_index("uk_dingtalk", "pc_user", ["dingtalk_userid"], unique=True,
                    postgresql_where=sa.text("dingtalk_userid IS NOT NULL"))
    op.create_index("uk_crm_user", "pc_user", ["crm_user_id"], unique=True,
                    postgresql_where=sa.text("crm_user_id IS NOT NULL"))

    # ── 去掉原有 (tenant_id, email) 的 NOT NULL name 限制，允许 email=NULL ──
    # name 字段改为可空（允许微信/手机号注册时不填姓名）
    op.alter_column("pc_user", "name", nullable=True)


def downgrade() -> None:
    op.alter_column("pc_user", "name", nullable=False)

    for idx in ["uk_wechat_unionid", "uk_wecom", "uk_feishu", "uk_dingtalk", "uk_crm_user"]:
        op.drop_index(idx, table_name="pc_user")

    for col in [
        "wechat_unionid", "wechat_openid_web", "wechat_openid_mp", "wechat_openid_oa",
        "wecom_userid", "wecom_corpid",
        "feishu_userid", "feishu_tenant_key",
        "dingtalk_userid", "crm_user_id",
        "industry", "register_source", "register_channel",
        "profile_completeness", "last_login_source",
    ]:
        op.drop_column("pc_user", col)
