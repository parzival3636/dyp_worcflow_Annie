"""
Telegram Notifier interface, formatting, and test fake.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Protocol

import httpx

from app.config import get_settings
from app.models.orm import ProposedTask

logger = logging.getLogger("transcribe.notifier")

_MD_ESCAPE_RE = re.compile(r"([_\*\[\]\(\)~`>#\+\-=\|{}\.!])")


def escape_markdown(text: str) -> str:
    """Escapes special characters for Telegram MarkdownV2."""
    if not text:
        return ""
    return _MD_ESCAPE_RE.sub(r"\\\1", text)


class Notifier(Protocol):
    async def send_text(self, chat_id: str, text: str) -> Optional[str]:
        ...

    async def send_task_card(self, chat_id: str, task: ProposedTask) -> Optional[str]:
        ...

    async def send_clarification(self, chat_id: str, task: ProposedTask, question: str) -> Optional[str]:
        ...

    async def edit_message(self, chat_id: str, message_id: str, text: str) -> bool:
        ...


class FakeNotifier:
    """Records sent messages for unit and integration testing."""

    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []
        self.edited_messages: List[Dict[str, Any]] = []

    async def send_text(self, chat_id: str, text: str) -> Optional[str]:
        msg_id = str(len(self.sent_messages) + 1)
        self.sent_messages.append({"chat_id": chat_id, "text": text, "message_id": msg_id, "type": "text"})
        return msg_id

    async def send_task_card(self, chat_id: str, task: ProposedTask) -> Optional[str]:
        msg_id = str(len(self.sent_messages) + 1)
        self.sent_messages.append({
            "chat_id": chat_id,
            "task_id": task.id,
            "title": task.title,
            "message_id": msg_id,
            "type": "card",
        })
        return msg_id

    async def send_clarification(self, chat_id: str, task: ProposedTask, question: str) -> Optional[str]:
        msg_id = str(len(self.sent_messages) + 1)
        self.sent_messages.append({
            "chat_id": chat_id,
            "task_id": task.id,
            "question": question,
            "message_id": msg_id,
            "type": "clarification",
        })
        return msg_id

    async def edit_message(self, chat_id: str, message_id: str, text: str) -> bool:
        self.edited_messages.append({"chat_id": chat_id, "message_id": message_id, "text": text})
        return True


class TelegramNotifier:
    """Sends messages and interactive cards using Telegram Bot API."""

    def __init__(self, bot_token: Optional[str] = None):
        settings = get_settings()
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"

    async def send_text(self, chat_id: str, text: str) -> Optional[str]:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "MarkdownV2",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.is_success:
                    data = resp.json()
                    return str(data.get("result", {}).get("message_id"))
        except Exception as e:
            logger.error("Failed to send telegram text: %s", e)
        return None

    async def send_task_card(self, chat_id: str, task: ProposedTask) -> Optional[str]:
        url = f"{self.base_url}/sendMessage"
        owner_display = escape_markdown(task.owner_raw or "Unassigned")
        deadline_display = escape_markdown(str(task.deadline_iso or task.deadline_raw or "No deadline"))
        title_display = escape_markdown(task.title)
        quote_display = escape_markdown(task.evidence[:150])
        conf_pct = int(task.confidence * 100)

        card_text = (
            f"📋 *Proposed Task*\n"
            f"• *Title:* {title_display}\n"
            f"• *Owner:* {owner_display}\n"
            f"• *Deadline:* {deadline_display}\n"
            f"• *Confidence:* {conf_pct}%\n"
            f"• *Evidence:* \"_{quote_display}_\""
        )

        buttons = [
            [
                {"text": "✅ Approve", "callback_data": f"tr:approve:{task.id}"},
                {"text": "✏️ Edit", "callback_data": f"tr:edit:{task.id}"},
                {"text": "❌ Reject", "callback_data": f"tr:reject:{task.id}"},
            ]
        ]

        payload = {
            "chat_id": chat_id,
            "text": card_text,
            "parse_mode": "MarkdownV2",
            "reply_markup": {"inline_keyboard": buttons},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.is_success:
                    return str(resp.json().get("result", {}).get("message_id"))
        except Exception as e:
            logger.error("Failed to send telegram task card: %s", e)
        return None

    async def send_clarification(self, chat_id: str, task: ProposedTask, question: str) -> Optional[str]:
        url = f"{self.base_url}/sendMessage"
        escaped_q = escape_markdown(question)
        payload = {
            "chat_id": chat_id,
            "text": f"❓ *Clarification Needed*\n{escaped_q}",
            "parse_mode": "MarkdownV2",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.is_success:
                    return str(resp.json().get("result", {}).get("message_id"))
        except Exception as e:
            logger.error("Failed to send telegram clarification: %s", e)
        return None

    async def edit_message(self, chat_id: str, message_id: str, text: str) -> bool:
        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": int(message_id),
            "text": text,
            "parse_mode": "MarkdownV2",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                return resp.is_success
        except Exception as e:
            logger.error("Failed to edit telegram message: %s", e)
        return False
