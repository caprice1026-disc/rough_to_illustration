from __future__ import annotations

from typing import Any

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from illust import MissingApiKeyError
from models import ChatAttachment, ChatMessage, ChatSession
from services.chat_service import (
    CHAT_MODES,
    add_message,
    chat_image_path,
    create_session,
    generate_text_reply,
    last_assistant_image,
    run_edit_mode,
    run_reference_mode,
    run_rough_mode,
    run_session_edit,
    save_uploaded_image,
    touch_session,
    update_session_title,
)
from services.generation_service import GenerationError


chat_bp = Blueprint("chat", __name__)


def _session_or_404(session_id: int) -> ChatSession:
    session = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
    if not session:
        abort(404)
    return session


def _serialize_message(message: ChatMessage) -> dict[str, Any]:
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
                "url": url_for("chat.image", image_id=attachment.image_id),
            }
            for attachment in message.attachments
        ],
    }


@chat_bp.route("/chat", methods=["GET"])
@login_required
def index() -> str:
    sessions = (
        ChatSession.query.filter_by(user_id=current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    session_id = request.args.get("session_id", type=int)
    selected: ChatSession | None = None

    if session_id:
        selected = ChatSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not selected:
            flash("指定されたチャットセッションが見つかりません。", "error")

    if selected is None:
        selected = sessions[0] if sessions else create_session(current_user.id, title="新しいチャット")
        if not sessions:
            sessions = [selected]

    last_image = last_assistant_image(selected)

    return render_template(
        "chat.html",
        chat_sessions=sessions,
        current_session=selected,
        chat_modes=CHAT_MODES,
        last_image=last_image,
    )


@chat_bp.route("/chat/new", methods=["POST"])
@login_required
def new_session() -> str:
    session = create_session(current_user.id, title="新しいチャット")
    return redirect(url_for("chat.index", session_id=session.id))


@chat_bp.route("/chat/images/<image_id>")
@login_required
def image(image_id: str):
    attachment = (
        ChatAttachment.query.join(ChatMessage)
        .join(ChatSession)
        .filter(ChatAttachment.image_id == image_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not attachment:
        abort(404)

    file_path = chat_image_path(image_id)
    if not file_path.exists():
        abort(404)
    return send_file(file_path, mimetype=attachment.mime_type)


@chat_bp.route("/chat/messages", methods=["POST"])
@login_required
def send_message():
    session_id = request.form.get("session_id", type=int)
    if not session_id:
        return jsonify({"error": "セッションが見つかりません。"}), 400

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
            attachments.append(("rough", save_uploaded_image(rough_file, label="ラフ画像")))
            user_text = f"色: {color_instruction}\nポーズ: {pose_instruction}".strip()
            add_message(session=session, role="user", text=user_text, mode_id=mode_id, attachments=attachments)
            update_session_title(session, user_text)
            result = run_rough_mode(
                rough_file=rough_file,
                color_instruction=color_instruction,
                pose_instruction=pose_instruction,
            )
            assistant_message = add_message(
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
            attachments.append(("reference", save_uploaded_image(reference_file, label="完成絵")))
            attachments.append(("rough", save_uploaded_image(rough_file, label="ラフ画像")))
            add_message(
                session=session,
                role="user",
                text="完成絵参照→ラフ着色を依頼",
                mode_id=mode_id,
                attachments=attachments,
            )
            update_session_title(session, "完成絵参照→ラフ着色を依頼")
            result = run_reference_mode(reference_file=reference_file, rough_file=rough_file)
            assistant_message = add_message(
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
            attachments.append(("base", save_uploaded_image(base_file, label="編集元画像")))
            attachments.append(("mask", save_uploaded_image(mask_file, label="マスク画像")))
            add_message(
                session=session,
                role="user",
                text=edit_instruction or "マスク編集を依頼",
                mode_id=mode_id,
                attachments=attachments,
            )
            update_session_title(session, edit_instruction or "マスク編集を依頼")
            result = run_edit_mode(
                base_file=base_file,
                mask_file=mask_file,
                edit_mode=edit_mode,
                edit_instruction=edit_instruction,
            )
            assistant_message = add_message(
                session=session,
                role="assistant",
                text="編集が完了しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        elif mode_id == "session_edit":
            if not user_message:
                raise GenerationError("追加編集の指示を入力してください。")
            add_message(session=session, role="user", text=user_message, mode_id=mode_id)
            update_session_title(session, user_message)
            result = run_session_edit(session, user_message)
            assistant_message = add_message(
                session=session,
                role="assistant",
                text="直近の画像をベースに再生成しました。",
                mode_id=mode_id,
                attachments=[("result", result)],
            )
        else:
            if not user_message:
                raise GenerationError("メッセージを入力してください。")
            add_message(session=session, role="user", text=user_message, mode_id=mode_id)
            update_session_title(session, user_message)
            reply = generate_text_reply(session, user_message)
            assistant_message = add_message(session=session, role="assistant", text=reply, mode_id=mode_id)

        touch_session(session)
    except MissingApiKeyError:
        return jsonify({"error": "APIキーが設定されていません。"}), 400
    except GenerationError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": "チャット処理に失敗しました。"}), 500

    return jsonify(
        {
            "assistant": _serialize_message(assistant_message),
        }
    )
