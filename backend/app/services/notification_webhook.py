"""
企业IM 通知 Webhook 服务

支持三大企业 IM 平台的群机器人 Webhook 消息推送：
  - 企业微信（Wecom）群机器人
  - 飞书（Feishu）群机器人
  - 钉钉（DingTalk）群机器人

配置（环境变量）：
  WECOM_WEBHOOK_URL   — 企微群机器人 Webhook 地址
  FEISHU_WEBHOOK_URL  — 飞书群机器人 Webhook 地址
  DINGTALK_WEBHOOK_URL — 钉钉群机器人 Webhook 地址

如果 URL 未配置，对应平台的推送静默跳过。
"""
from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _post_json(url: str, payload: dict[str, Any], timeout: int = 8) -> bool:
    """POST JSON payload to URL. Returns True on success."""
    if not url:
        return False
    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status < 300
    except Exception as e:
        logger.warning("Notification webhook failed (%s): %s", url[:40], e)
        return False


# ─── 企业微信 群机器人 ───────────────────────────────────────────────────────

def send_wecom(
    webhook_url: str,
    title: str,
    content: str,
    color: str = "warning",
) -> bool:
    """
    发送企微群机器人消息（markdown 格式）。
    color: info | warning | comment
    """
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"## {title}\n\n{content}"
        },
    }
    return _post_json(webhook_url, payload)


# ─── 飞书 群机器人 ──────────────────────────────────────────────────────────

def send_feishu(
    webhook_url: str,
    title: str,
    content: str,
) -> bool:
    """
    发送飞书群机器人消息（富文本 post 格式）。
    """
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": [[{"tag": "text", "text": content}]],
                }
            }
        },
    }
    return _post_json(webhook_url, payload)


# ─── 钉钉 群机器人 ──────────────────────────────────────────────────────────

def send_dingtalk(
    webhook_url: str,
    title: str,
    content: str,
) -> bool:
    """
    发送钉钉群机器人消息（markdown 格式）。
    """
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": f"## {title}\n\n{content}",
        },
    }
    return _post_json(webhook_url, payload)


# ─── 统一推送接口 ───────────────────────────────────────────────────────────

def broadcast_to_all(title: str, content: str) -> dict[str, bool]:
    """
    同时推送到所有已配置的企业 IM 渠道。
    返回每个渠道的推送结果。

    配置优先级：环境变量 > settings 对象属性。
    """
    wecom_url = getattr(settings, "wecom_webhook_url", "")
    feishu_url = getattr(settings, "feishu_webhook_url", "")
    dingtalk_url = getattr(settings, "dingtalk_webhook_url", "")

    results: dict[str, bool] = {}

    if wecom_url:
        results["wecom"] = send_wecom(wecom_url, title, content)

    if feishu_url:
        results["feishu"] = send_feishu(feishu_url, title, content)

    if dingtalk_url:
        results["dingtalk"] = send_dingtalk(dingtalk_url, title, content)

    if not results:
        logger.debug("No enterprise IM webhook configured; skipping notification broadcast.")

    return results


# ─── 预定义消息模板 ─────────────────────────────────────────────────────────

def notify_bid_deadline(
    task_name: str,
    hours_left: int,
    responsible_name: str,
    readiness_pct: int,
) -> dict[str, bool]:
    """述标 48 小时预警通知"""
    title = f"⏰ 述标倒计时预警 — {task_name}"
    content = (
        f"**项目**：{task_name}\n"
        f"**负责人**：{responsible_name}\n"
        f"**剩余时间**：约 {hours_left} 小时\n"
        f"**当前就绪度**：{readiness_pct}%\n\n"
        f"请尽快完成剩余 SOP 步骤，确保述标万全准备！"
    )
    return broadcast_to_all(title, content)


def notify_review_requested(
    task_name: str,
    member_name: str,
    manager_name: str,
) -> dict[str, bool]:
    """排练提交审核通知（发给经理）"""
    title = f"📋 审核请求 — {task_name}"
    content = (
        f"**{member_name}** 已提交排练，请 **{manager_name}** 审核并认证。\n"
        f"项目：{task_name}"
    )
    return broadcast_to_all(title, content)


def notify_certification_result(
    task_name: str,
    member_name: str,
    passed: bool,
    comments: str = "",
) -> dict[str, bool]:
    """认证结果通知"""
    status = "✅ 通过" if passed else "❌ 未通过"
    title = f"{status} — {task_name} 述标认证"
    content = (
        f"**{member_name}** 的述标认证结果：{status}\n"
        f"项目：{task_name}"
    )
    if comments:
        content += f"\n审核意见：{comments}"
    return broadcast_to_all(title, content)
