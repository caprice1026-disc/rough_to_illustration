from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from flask import session
from PIL import Image

from services.generation_service import load_image_path_from_storage


DEFAULT_CHAT_SYSTEM_PROMPT = (
    "あなたはイラスト制作の相談に乗るアシスタントです。"
    "会話履歴を参照しつつ、簡潔でわかりやすい日本語で返答してください。"
)


@dataclass(frozen=True)
class ChatImage:
    """チャットメッセージに紐づく画像情報。"""

    image_id: str
    mime_type: str
    label: str = ""


@dataclass(frozen=True)
class ChatMessage:
    """チャットのメッセージデータ。"""

    role: str
    text: str
    images: list[ChatImage] = field(default_factory=list)


def _serialize_message(message: ChatMessage) -> dict:
    return {
        "role": message.role,
        "text": message.text,
        "images": [
            {"image_id": image.image_id, "mime_type": image.mime_type, "label": image.label}
            for image in message.images
        ],
    }


def _deserialize_message(raw: dict) -> ChatMessage:
    images = [
        ChatImage(
            image_id=image.get("image_id", ""),
            mime_type=image.get("mime_type", "image/png"),
            label=image.get("label", ""),
        )
        for image in raw.get("images", [])
        if image.get("image_id")
    ]
    return ChatMessage(
        role=raw.get("role", "user"),
        text=raw.get("text", ""),
        images=images,
    )


def load_chat_history() -> list[ChatMessage]:
    """セッションに保存したチャット履歴を取得する。"""

    raw_history = session.get("chat_history", [])
    if not isinstance(raw_history, list):
        return []
    return [_deserialize_message(item) for item in raw_history if isinstance(item, dict)]


def save_chat_history(history: Iterable[ChatMessage]) -> None:
    """チャット履歴をセッションに保存する。"""

    session["chat_history"] = [_serialize_message(message) for message in history]


def clear_chat_history() -> None:
    """チャット履歴をクリアする。"""

    session.pop("chat_history", None)


def append_chat_message(
    history: list[ChatMessage],
    message: ChatMessage,
    *,
    max_messages: int = 24,
) -> list[ChatMessage]:
    """チャット履歴にメッセージを追加し、上限件数でトリムする。"""

    updated = [*history, message]
    if len(updated) > max_messages:
        updated = updated[-max_messages:]
    save_chat_history(updated)
    return updated


def build_chat_contents(
    history: list[ChatMessage],
    *,
    system_prompt: str = DEFAULT_CHAT_SYSTEM_PROMPT,
) -> list[object]:
    """Geminiに渡すチャットコンテンツを構築する。"""

    contents: list[object] = []
    if system_prompt:
        contents.append(system_prompt)

    for message in history:
        role_label = "ユーザー" if message.role == "user" else "アシスタント"
        text = message.text.strip() or "（内容なし）"
        contents.append(f"{role_label}: {text}")
        if message.role == "user":
            contents.extend(_load_message_images(message))

    return contents


def _load_message_images(message: ChatMessage) -> list[Image.Image]:
    images: list[Image.Image] = []
    for image_info in message.images:
        path = load_image_path_from_storage(image_info.image_id)
        if not path or not path.exists():
            continue
        try:
            image = Image.open(path)
            image.load()
        except Exception:
            continue
        images.append(image)
    return images


def build_user_message(
    *,
    text: str,
    images: Optional[list[ChatImage]] = None,
) -> ChatMessage:
    """ユーザー発話用のメッセージを生成する。"""

    return ChatMessage(role="user", text=text, images=images or [])


def build_assistant_message(
    text: str,
    *,
    images: Optional[list[ChatImage]] = None,
) -> ChatMessage:
    """アシスタント発話用のメッセージを生成する。"""

    return ChatMessage(role="assistant", text=text, images=images or [])
