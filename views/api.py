from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from flask import Blueprint, abort, current_app, jsonify, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf

from extensions import db
from illust import MissingApiKeyError
from models import ChatAttachment, ChatMessage, ChatSession, IllustrationPreset, User
from services import chat_service
from services.generation_service import (
    GenerationError,
    extension_for_mime_type,
    load_image_path_from_session,
    load_mime_type_from_session,
    run_edit_generation,
    run_generation,
    run_generation_with_reference,
    save_result_to_session,
)
from services.modes import (
    ALL_MODES,
    MODE_INPAINT_OUTPAINT,
    MODE_REFERENCE_STYLE_COLORIZE,
    MODE_ROUGH_WITH_INSTRUCTIONS,
    normalize_mode_id,
)


api_bp = Blueprint("api", __name__, url_prefix="/api")

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]


def _json(payload: dict[str, Any], status: int = 200):
    return jsonify(payload), status


def _error(message: str, status: int = 400):
    return _json({"error": message}, status)


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_initial_user": user.is_initial_user,
    }


def _serialize_preset(preset: IllustrationPreset) -> dict[str, Any]:
    return {
        "id": preset.id,
        "name": preset.name,
        "color_instruction": preset.color_instruction,
        "pose_instruction": preset.pose_instruction,
        "created_at": preset.created_at.isoformat() if preset.created_at else "",
    }


def _serialize_generation(result) -> dict[str, Any]:
    return {
        "image_data_uri": result.image_data_uri,
        "mime_type": result.mime_type,
        "image_id": result.image_id,
    }


def _serialize_chat_mode(mode: chat_service.ChatMode) -> dict[str, Any]:
    return {
        "id": mode.id,
        "label": mode.label,
        "description": mode.description,
        "helper": mode.helper,
    }


def _serialize_chat_message(message: ChatMessage) -> dict[str, Any]:
    return {
        "id": message.id,
        "role": message.role,
        "text": message.text or "",
        "mode_id": message.mode_id,
        "created_at": message.created_at.isoformat() if message.created_at else "",
        "attachments": [
            {
                "kind": attachment.kind,
                "mime_type": attachment.mime_type,
                "url": url_for("api.chat_image", image_id=attachment.image_id),
            }
            for attachment in message.attachments
        ],
    }


def _serialize_chat_session(session: ChatSession, *, include_messages: bool = False) -> dict[str, Any]:
    payload = {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "updated_at": session.updated_at.isoformat() if session.updated_at else "",
    }
    if include_messages:
        payload["messages"] = [_serialize_chat_message(message) for message in session.messages]
    return payload


def _session_or_404(session_id: int) -> ChatSession:
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        abort(404)
    return session


def _extract_payload() -> dict[str, Any]:
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return {}


@api_bp.get("/health")
def health():
    return _json({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


@api_bp.get("/csrf")
def csrf_token():
    return _json({"csrf_token": generate_csrf()})


@api_bp.get("/me")
def me():
    if not current_user.is_authenticated:
        return _json({"authenticated": False})
    return _json({"authenticated": True, "user": _serialize_user(current_user)})


@api_bp.post("/auth/login")
def login():
    if current_user.is_authenticated:
        return _json({"user": _serialize_user(current_user)})

    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return _error("ユーザー名とパスワードを入力してください。", 400)

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return _error("ユーザー名またはパスワードが違います。", 401)

    login_user(user)
    return _json({"user": _serialize_user(user)})


@api_bp.post("/auth/logout")
@login_required
def logout():
    logout_user()
    return _json({"ok": True})


@api_bp.post("/auth/signup")
@login_required
def signup():
    if not current_user.is_initial_user:
        return _error("初期ユーザーのみが新規登録できます。", 403)

    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return _error("すべての項目を入力してください。", 400)

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return _error("同じユーザー名またはメールアドレスが既に存在します。", 400)

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return _json({"user": _serialize_user(user)}, 201)


@api_bp.get("/modes")
def modes():
    return _json(
        {
            "modes": [
                {
                    "id": mode.id,
                    "label": mode.label,
                    "description": mode.description,
                    "enabled": mode.enabled,
                }
                for mode in ALL_MODES
            ]
        }
    )


@api_bp.get("/options")
def options():
    return _json({"aspect_ratio_options": ASPECT_RATIO_OPTIONS, "resolution_options": RESOLUTION_OPTIONS})


@api_bp.get("/presets")
@login_required
def presets():
    presets_list = (
        IllustrationPreset.query.filter_by(user_id=current_user.id)
        .order_by(IllustrationPreset.created_at.desc())
        .all()
    )
    return _json({"presets": [_serialize_preset(preset) for preset in presets_list]})


@api_bp.post("/presets")
@login_required
def create_preset():
    data = _extract_payload()
    if not data:
        data = request.form.to_dict()

    mode = normalize_mode_id(data.get("mode"))
    name = (data.get("name") or "").strip()
    color_instruction = (data.get("color_instruction") or "").strip()
    pose_instruction = (data.get("pose_instruction") or "").strip()

    if not name:
        return _error("プリセット名を入力してください。", 400)

    if len(name) > 80:
        return _error("プリセット名は80文字以内にしてください。", 400)

    if mode in {MODE_REFERENCE_STYLE_COLORIZE.id, MODE_INPAINT_OUTPAINT.id}:
        if not color_instruction:
            return _error("追加指示を入力してください。", 400)
        pose_instruction = ""
        if len(color_instruction) > 1000:
            return _error("文字数上限を超えています。入力内容を短くしてください。", 400)
    else:
        if not color_instruction or not pose_instruction:
            return _error("色とポーズの指示を両方入力してください。", 400)
        if len(color_instruction) > 200 or len(pose_instruction) > 160:
            return _error("文字数上限を超えています。入力内容を短くしてください。", 400)

    preset = IllustrationPreset(
        user_id=current_user.id,
        name=name,
        color_instruction=color_instruction,
        pose_instruction=pose_instruction,
    )
    db.session.add(preset)
    db.session.commit()
    return _json({"preset": _serialize_preset(preset)}, 201)


@api_bp.delete("/presets/<int:preset_id>")
@login_required
def delete_preset(preset_id: int):
    preset = IllustrationPreset.query.filter_by(id=preset_id, user_id=current_user.id).first()
    if not preset:
        return _error("指定されたプリセットが見つかりません。", 404)

    db.session.delete(preset)
    db.session.commit()
    return _json({"ok": True})


@api_bp.post("/generate/rough")
@login_required
def generate_rough():
    aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
    resolution_label = request.form.get("resolution") or "auto"
    file = request.files.get("rough_image")
    color_instruction = request.form.get("color_instruction", "")
    pose_instruction = request.form.get("pose_instruction", "")

    try:
        result = run_generation(
            file=file,
            color_instruction=color_instruction,
            pose_instruction=pose_instruction,
            aspect_ratio_label=aspect_ratio_label,
            resolution_label=resolution_label,
        )
        save_result_to_session(result)
    except GenerationError as exc:
        return _error(str(exc), 400)
    except MissingApiKeyError:
        current_app.logger.error("Missing API key for image generation.")
        return _error("APIキーが設定されていません。", 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Image generation failed: %s", exc)
        return _error("画像生成に失敗しました。", 500)

    return _json({"result": _serialize_generation(result)})


@api_bp.post("/generate/reference")
@login_required
def generate_reference():
    aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
    resolution_label = request.form.get("resolution") or "auto"
    reference_file = request.files.get("reference_image")
    rough_file = request.files.get("rough_image")
    reference_instruction = request.form.get("reference_instruction", "")

    try:
        result = run_generation_with_reference(
            reference_file=reference_file,
            rough_file=rough_file,
            reference_instruction=reference_instruction,
            aspect_ratio_label=aspect_ratio_label,
            resolution_label=resolution_label,
        )
        save_result_to_session(result)
    except GenerationError as exc:
        return _error(str(exc), 400)
    except MissingApiKeyError:
        current_app.logger.error("Missing API key for image generation.")
        return _error("APIキーが設定されていません。", 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Image generation failed: %s", exc)
        return _error("画像生成に失敗しました。", 500)

    return _json({"result": _serialize_generation(result)})


@api_bp.post("/generate/edit")
@login_required
def generate_edit():
    base_file = request.files.get("edit_base_image")
    mask_file = request.files.get("edit_mask_image")
    base_data = request.form.get("edit_base_data")
    mask_data = request.form.get("edit_mask_data")
    edit_mode = request.form.get("edit_mode", "inpaint")
    edit_instruction = request.form.get("edit_instruction", "")

    try:
        result = run_edit_generation(
            base_file=base_file,
            base_data=base_data,
            mask_file=mask_file,
            mask_data=mask_data,
            edit_mode=edit_mode,
            edit_instruction=edit_instruction,
        )
        save_result_to_session(result)
    except GenerationError as exc:
        return _error(str(exc), 400)
    except MissingApiKeyError:
        current_app.logger.error("Missing API key for image generation.")
        return _error("APIキーが設定されていません。", 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Image generation failed: %s", exc)
        return _error("画像生成に失敗しました。", 500)

    return _json({"result": _serialize_generation(result)})


@api_bp.get("/generated/<image_id>")
@login_required
def generated(image_id: str):
    image_path = load_image_path_from_session()
    if not image_path or image_path.name != image_id:
        abort(404)

    mime_type = load_mime_type_from_session()
    return send_file(
        image_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=f"generated_image{extension_for_mime_type(mime_type)}",
    )


@api_bp.get("/chat/modes")
@login_required
def chat_modes():
    return _json({"modes": [_serialize_chat_mode(mode) for mode in chat_service.CHAT_MODES]})


@api_bp.get("/chat/sessions")
@login_required
def chat_sessions():
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    if not sessions:
        session = chat_service.create_session(current_user.id, title="新しいチャット")
        sessions = [session]
    return _json({"sessions": [_serialize_chat_session(session) for session in sessions]})


@api_bp.post("/chat/sessions")
@login_required
def create_chat_session():
    data = _extract_payload()
    title = (data.get("title") or "").strip() or "新しいチャット"
    session = chat_service.create_session(current_user.id, title=title)
    return _json({"session": _serialize_chat_session(session)}, 201)


@api_bp.get("/chat/sessions/<int:session_id>")
@login_required
def chat_session_detail(session_id: int):
    session = _session_or_404(session_id)
    return _json({"session": _serialize_chat_session(session, include_messages=True)})


@api_bp.get("/chat/images/<image_id>")
@login_required
def chat_image(image_id: str):
    attachment = (
        ChatAttachment.query.join(ChatMessage)
        .join(ChatSession)
        .filter(ChatAttachment.image_id == image_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not attachment:
        abort(404)

    raw_bytes = chat_service.load_chat_image_bytes(image_id)
    if raw_bytes is None:
        abort(404)
    return send_file(BytesIO(raw_bytes), mimetype=attachment.mime_type)


@api_bp.post("/chat/messages")
@login_required
def chat_messages():
    session_id = request.form.get("session_id", type=int)
    if not session_id:
        return _error("セッションが見つかりません。", 400)

    session = _session_or_404(session_id)
    mode_id = request.form.get("mode_id") or "text_chat"
    user_message = (request.form.get("message") or "").strip()

    try:
        attachments = []
        if mode_id == "rough_with_instructions":
            rough_file = request.files.get("rough_image")
            color_instruction = request.form.get("color_instruction", "")
            pose_instruction = request.form.get("pose_instruction", "")
            if not rough_file:
                raise GenerationError("ラフ画像を選択してください。")
            attachments.append(("rough", chat_service.save_uploaded_image(rough_file, label="ラフ画像")))
            user_text = f"色: {color_instruction}\nポーズ: {pose_instruction}".strip()
            chat_service.add_message(session=session, role="user", text=user_text, mode_id=mode_id, attachments=attachments)
            chat_service.update_session_title(session, user_text)
            result = chat_service.run_rough_mode(
                rough_file=rough_file,
                color_instruction=color_instruction,
                pose_instruction=pose_instruction,
            )
            assistant_message = chat_service.add_message(
                session=session,
                role="assistant",
                text="イラスト生成が完了しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        elif mode_id == "reference_style_colorize":
            reference_file = request.files.get("reference_image")
            rough_file = request.files.get("rough_image")
            if not reference_file or not rough_file:
                raise GenerationError("完成絵とラフ画像の両方を選択してください。")
            attachments.append(("reference", chat_service.save_uploaded_image(reference_file, label="完成絵")))
            attachments.append(("rough", chat_service.save_uploaded_image(rough_file, label="ラフ画像")))
            chat_service.add_message(
                session=session,
                role="user",
                text="完成絵参照→ラフ着色を依頼",
                mode_id=mode_id,
                attachments=attachments,
            )
            chat_service.update_session_title(session, "完成絵参照→ラフ着色を依頼")
            result = chat_service.run_reference_mode(reference_file=reference_file, rough_file=rough_file)
            assistant_message = chat_service.add_message(
                session=session,
                role="assistant",
                text="参照を反映した仕上げが完了しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        elif mode_id == "inpaint_outpaint":
            base_file = request.files.get("edit_base_image")
            mask_file = request.files.get("edit_mask_image")
            edit_mode = request.form.get("edit_mode", "inpaint")
            edit_instruction = request.form.get("edit_instruction", "")
            if not base_file or not mask_file:
                raise GenerationError("編集元画像とマスク画像を選択してください。")
            attachments.append(("base", chat_service.save_uploaded_image(base_file, label="編集元画像")))
            attachments.append(("mask", chat_service.save_uploaded_image(mask_file, label="マスク画像")))
            chat_service.add_message(
                session=session,
                role="user",
                text=edit_instruction or "マスク編集を依頼",
                mode_id=mode_id,
                attachments=attachments,
            )
            chat_service.update_session_title(session, edit_instruction or "マスク編集を依頼")
            result = chat_service.run_edit_mode(
                base_file=base_file,
                mask_file=mask_file,
                edit_mode=edit_mode,
                edit_instruction=edit_instruction,
            )
            assistant_message = chat_service.add_message(
                session=session,
                role="assistant",
                text="編集が完了しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        elif mode_id == "session_edit":
            if not user_message:
                raise GenerationError("追加編集指示を入力してください。")
            chat_service.add_message(session=session, role="user", text=user_message, mode_id=mode_id)
            chat_service.update_session_title(session, user_message)
            result = chat_service.run_session_edit(session, user_message)
            assistant_message = chat_service.add_message(
                session=session,
                role="assistant",
                text="直近の画像をベースに再生成しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        else:
            if not user_message:
                raise GenerationError("メッセージを入力してください。")
            chat_service.add_message(session=session, role="user", text=user_message, mode_id=mode_id)
            chat_service.update_session_title(session, user_message)
            reply = chat_service.generate_text_reply(session, user_message)
            assistant_message = chat_service.add_message(
                session=session,
                role="assistant",
                text=reply,
                mode_id=mode_id,
            )

        chat_service.touch_session(session)
    except MissingApiKeyError:
        return _error("APIキーが設定されていません。", 400)
    except GenerationError as exc:
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Chat handling failed: %s", exc)
        return _error("チャット処理に失敗しました。", 500)

    return _json({"assistant": _serialize_chat_message(assistant_message)})
