from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

from flask import current_app
from google.api_core.exceptions import NotFound
from google.cloud import storage
from PIL import Image
from werkzeug.datastructures import FileStorage

from extensions import db
from illust import edit_image_with_mask, generate_image, generate_image_with_contents, generate_text
from models import ChatAttachment, ChatMessage, ChatSession
from services.generation_service import (
    GenerationError,
    decode_image_bytes,
    decode_uploaded_image_raw,
    ensure_rgb,
    extension_for_mime_type,
    mime_type_for_image,
    normalize_mask_image,
    read_uploaded_bytes,
)
from services.prompt_builder import (
    build_chat_edit_prompt,
    build_edit_prompt,
    build_prompt,
    build_reference_style_colorize_prompt,
)


@dataclass(frozen=True)
class ChatMode:
    """チャット画面で選択できるモード定義。"""

    id: str
    label: str
    description: str
    helper: str


CHAT_MODE_TEXT = ChatMode(
    id="text_chat",
    label="テキストチャット",
    description="テキスト相談や質問を行う基本モードです。",
    helper="テキストのみで送信します。",
)

CHAT_MODE_SESSION_EDIT = ChatMode(
    id="session_edit",
    label="前の結果を追加編集",
    description="直近の生成画像にテキスト指示を加えて再生成します。",
    helper="直近の画像が必要です。",
)

CHAT_MODE_ROUGH = ChatMode(
    id="rough_with_instructions",
    label="ラフ→仕上げ（色・ポーズ指示）",
    description="ラフスケッチ1枚とテキスト指示で仕上げます。",
    helper="ラフ画像と色・ポーズ指示を入力してください。",
)

CHAT_MODE_REFERENCE = ChatMode(
    id="reference_style_colorize",
    label="完成絵参照→ラフ着色（2枚）",
    description="完成絵のタッチを参考にラフを仕上げます。",
    helper="完成絵とラフ画像の2枚が必要です。",
)

CHAT_MODE_EDIT = ChatMode(
    id="inpaint_outpaint",
    label="インペイント/アウトペイント編集",
    description="マスクで指定した領域を編集します。",
    helper="ベース画像とマスク画像が必要です。",
)

CHAT_MODES: list[ChatMode] = [
    CHAT_MODE_TEXT,
    CHAT_MODE_SESSION_EDIT,
    CHAT_MODE_ROUGH,
    CHAT_MODE_REFERENCE,
    CHAT_MODE_EDIT,
]


@dataclass
class StoredImage:
    image_id: str
    mime_type: str


def _chat_image_object_name(image_id: str) -> str:
    safe_name = Path(image_id).name
    return f"chat_images/{safe_name}"


def _chat_image_storage_mode() -> str:
    return (current_app.config.get("CHAT_IMAGE_STORAGE") or "local").strip().lower()


def _chat_image_local_dir() -> Path:
    base = current_app.config.get("CHAT_IMAGE_DIR") or "chat_images"
    path = Path(base)
    if not path.is_absolute():
        path = Path(current_app.instance_path) / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _chat_image_bucket() -> storage.Bucket:
    if _chat_image_storage_mode() != "gcs":
        raise GenerationError("CHAT_IMAGE_STORAGE が gcs ではありません。")
    bucket_name = current_app.config.get("CHAT_IMAGE_BUCKET")
    if not bucket_name:
        raise GenerationError("CHAT_IMAGE_BUCKET が設定されていません。")
    client = storage.Client()
    return client.bucket(bucket_name)


def _chat_image_blob(image_id: str) -> storage.Blob:
    return _chat_image_bucket().blob(_chat_image_object_name(image_id))


def persist_chat_image(raw_bytes: bytes, mime_type: str) -> StoredImage:
    image_id = f"{uuid4().hex}{extension_for_mime_type(mime_type)}"
    if _chat_image_storage_mode() == "gcs":
        blob = _chat_image_blob(image_id)
        blob.upload_from_string(raw_bytes, content_type=mime_type)
    else:
        target = _chat_image_local_dir() / image_id
        target.write_bytes(raw_bytes)
    return StoredImage(image_id=image_id, mime_type=mime_type)


def load_chat_image_bytes(image_id: str) -> Optional[bytes]:
    if _chat_image_storage_mode() == "gcs":
        blob = _chat_image_blob(image_id)
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None
    local_path = _chat_image_local_dir() / Path(image_id).name
    if not local_path.exists():
        return None
    return local_path.read_bytes()


def save_uploaded_image(file: Optional[FileStorage], *, label: str) -> StoredImage:
    raw_bytes, filename, mime_type = read_uploaded_bytes(file, label=label, reset_stream=True)
    image = decode_image_bytes(
        raw_bytes,
        label=label,
        filename=filename,
        mime_type=mime_type,
        convert_to_rgb=False,
    )
    return persist_chat_image(raw_bytes, mime_type_for_image(image))


def create_session(user_id: int, *, title: str) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.session.add(session)
    db.session.commit()
    return session


def touch_session(session: ChatSession) -> None:
    session.updated_at = db.func.now()
    db.session.add(session)
    db.session.commit()


def update_session_title(session: ChatSession, user_text: str) -> None:
    if session.title != "新しいチャット":
        return
    trimmed = user_text.strip()
    if not trimmed:
        return
    session.title = trimmed[:30]
    db.session.add(session)
    db.session.commit()


def add_message(
    *,
    session: ChatSession,
    role: str,
    text: Optional[str] = None,
    mode_id: Optional[str] = None,
    attachments: Optional[Iterable[tuple[str, StoredImage]]] = None,
) -> ChatMessage:
    message = ChatMessage(session=session, role=role, text=text, mode_id=mode_id)
    db.session.add(message)
    if attachments:
        for kind, stored in attachments:
            db.session.add(
                ChatAttachment(
                    message=message,
                    kind=kind,
                    image_id=stored.image_id,
                    mime_type=stored.mime_type,
                )
            )
    db.session.commit()
    return message


def fetch_recent_text_history(session: ChatSession, *, limit: int = 8) -> list[ChatMessage]:
    return (
        ChatMessage.query.filter_by(session_id=session.id)
        .filter(ChatMessage.text.isnot(None))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()[::-1]
    )


def build_text_prompt(history: list[ChatMessage], user_text: str) -> str:
    lines = [
        "あなたはイラスト制作の相談に乗るアシスタントです。",
        "以下はユーザーとの会話履歴です。",
    ]
    for message in history:
        role = "ユーザー" if message.role == "user" else "アシスタント"
        if message.text:
            lines.append(f"{role}: {message.text}")
    lines.append("---")
    lines.append(f"ユーザー: {user_text}")
    lines.append("アシスタント: ")
    return "\n".join(lines)


def generate_text_reply(session: ChatSession, user_text: str) -> str:
    history = fetch_recent_text_history(session)
    if history and history[-1].role == "user" and history[-1].text == user_text:
        history = history[:-1]
    prompt = build_text_prompt(history, user_text)
    return generate_text(prompt)


def last_assistant_image(session: ChatSession) -> Optional[StoredImage]:
    attachment = (
        ChatAttachment.query.join(ChatMessage)
        .filter(ChatMessage.session_id == session.id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc())
        .first()
    )
    if not attachment:
        return None
    return StoredImage(image_id=attachment.image_id, mime_type=attachment.mime_type)


def run_session_edit(session: ChatSession, user_text: str) -> StoredImage:
    stored = last_assistant_image(session)
    if not stored:
        raise GenerationError("直近の生成画像が見つかりません。先に画像生成を行ってください。")

    raw_bytes = load_chat_image_bytes(stored.image_id)
    if raw_bytes is None:
        raise GenerationError("前回の画像データが見つかりません。再度生成してください。")

    image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    prompt = build_chat_edit_prompt(user_text)
    generated = generate_image(prompt=prompt, image=image)
    return persist_chat_image(generated.raw_bytes, generated.mime_type)


def run_rough_mode(
    *,
    rough_file: Optional[FileStorage],
    color_instruction: str,
    pose_instruction: str,
) -> StoredImage:
    rough_image = decode_uploaded_image_raw(rough_file, label="ラフ絵")
    prompt = build_prompt(color_instruction, pose_instruction)
    generated = generate_image(prompt=prompt, image=rough_image)
    return persist_chat_image(generated.raw_bytes, generated.mime_type)


def run_reference_mode(
    *,
    reference_file: Optional[FileStorage],
    rough_file: Optional[FileStorage],
) -> StoredImage:
    reference_image = decode_uploaded_image_raw(reference_file, label="参考（完成）画像")
    rough_image = decode_uploaded_image_raw(rough_file, label="ラフスケッチ")
    prompt = build_reference_style_colorize_prompt()
    contents = [
        "これから2枚の画像を渡します。1枚目は編集対象のラフスケッチです。",
        rough_image,
        "次に2枚目を渡します。2枚目は画風・質感・陰影・彩度レンジの参照となる完成済みイラストです。",
        reference_image,
        prompt,
    ]
    generated = generate_image_with_contents(contents=contents, prompt_for_record=prompt)
    return persist_chat_image(generated.raw_bytes, generated.mime_type)


def run_edit_mode(
    *,
    base_file: Optional[FileStorage],
    mask_file: Optional[FileStorage],
    edit_mode: str,
    edit_instruction: str,
) -> StoredImage:
    base_image = decode_uploaded_image_raw(base_file, label="編集元画像")
    mask_image = decode_uploaded_image_raw(mask_file, label="マスク画像")
    base_image = ensure_rgb(base_image)
    mask_image = normalize_mask_image(mask_image)

    if base_image.size != mask_image.size:
        raise GenerationError("マスク画像のサイズがベース画像と一致しません。")

    normalized_mode = "outpaint" if edit_mode == "outpaint" else "inpaint"
    prompt = build_edit_prompt(edit_instruction, normalized_mode)
    generated = edit_image_with_mask(
        prompt=prompt,
        base_image=base_image,
        mask_image=mask_image,
        edit_mode=normalized_mode,
    )
    return persist_chat_image(generated.raw_bytes, generated.mime_type)
