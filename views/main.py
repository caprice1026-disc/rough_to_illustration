from __future__ import annotations

from typing import Optional

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from illust import MissingApiKeyError, generate_chat_response
from extensions import db
from models import IllustrationPreset
from services.chat_service import (
    ChatImage,
    append_chat_message,
    build_assistant_message,
    build_chat_contents,
    build_user_message,
    clear_chat_history,
    load_chat_history,
)
from services.generation_service import (
    GenerationError,
    extension_for_mime_type,
    load_image_data_uri,
    load_image_path_from_session,
    load_mime_type_from_session,
    load_result_from_session,
    persist_image_bytes,
    run_generation,
    run_generation_with_reference,
    run_edit_generation,
    save_result_to_session,
)
from services.modes import (
    ALL_MODES,
    MODE_CHAT_GUI,
    MODE_INPAINT_OUTPAINT,
    MODE_REFERENCE_STYLE_COLORIZE,
    normalize_mode_id,
)


main_bp = Blueprint("main", __name__)

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]


def _restore_result() -> Optional[str]:
    """セッションに保存された結果から表示用データを復元する。"""

    existing = load_result_from_session()
    if not existing:
        return None
    return existing.image_data_uri


def _fetch_presets() -> list[IllustrationPreset]:
    """現在のユーザーに紐づくプリセットを新しい順で取得する。"""

    if not current_user.is_authenticated:
        return []

    return (
        IllustrationPreset.query.filter_by(user_id=current_user.id)
        .order_by(IllustrationPreset.created_at.desc())
        .all()
    )


@main_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    image_data: Optional[str] = None
    current_mode = normalize_mode_id(request.form.get("mode") or request.args.get("mode"))
    chat_history = load_chat_history()

    if request.method == "POST":
        try:
            if current_mode == MODE_CHAT_GUI.id:
                aspect_ratio_label = request.form.get("chat_aspect_ratio") or "auto"
                resolution_label = request.form.get("chat_resolution") or "auto"
                action = request.form.get("chat_action", "text")
                if action == "clear":
                    clear_chat_history()
                    flash("チャット履歴をクリアしました。", "info")
                    return redirect(url_for("main.index", mode=current_mode))

                if action == "generate":
                    chat_mode = normalize_mode_id(request.form.get("chat_mode"))
                    if chat_mode == MODE_CHAT_GUI.id:
                        flash("チャットメニューのモードが不正です。", "error")
                        return redirect(url_for("main.index", mode=current_mode))

                    if chat_mode == MODE_REFERENCE_STYLE_COLORIZE.id:
                        reference_file = request.files.get("chat_reference_image")
                        rough_file = request.files.get("chat_rough_image")

                        user_images = []
                        if rough_file and rough_file.filename:
                            rough_bytes = rough_file.read()
                            rough_mime = rough_file.mimetype or "image/png"
                            rough_id = persist_image_bytes(raw_bytes=rough_bytes, mime_type=rough_mime)
                            rough_file.stream.seek(0)
                            user_images.append(ChatImage(image_id=rough_id, mime_type=rough_mime, label="ラフ"))
                        if reference_file and reference_file.filename:
                            reference_bytes = reference_file.read()
                            reference_mime = reference_file.mimetype or "image/png"
                            reference_id = persist_image_bytes(raw_bytes=reference_bytes, mime_type=reference_mime)
                            reference_file.stream.seek(0)
                            user_images.append(
                                ChatImage(image_id=reference_id, mime_type=reference_mime, label="参照画像")
                            )

                        user_text = "メニュー: 完成絵参照→ラフ着色"
                        chat_history = append_chat_message(
                            chat_history,
                            build_user_message(text=user_text, images=user_images),
                        )

                        result = run_generation_with_reference(
                            reference_file=reference_file,
                            rough_file=rough_file,
                            aspect_ratio_label=aspect_ratio_label,
                            resolution_label=resolution_label,
                        )
                    elif chat_mode == MODE_INPAINT_OUTPAINT.id:
                        base_file = request.files.get("chat_edit_base_image")
                        mask_file = request.files.get("chat_edit_mask_image")
                        edit_mode = request.form.get("chat_edit_mode", "inpaint")
                        edit_instruction = request.form.get("chat_edit_instruction", "")

                        user_images = []
                        if base_file and base_file.filename:
                            base_bytes = base_file.read()
                            base_mime = base_file.mimetype or "image/png"
                            base_id = persist_image_bytes(raw_bytes=base_bytes, mime_type=base_mime)
                            base_file.stream.seek(0)
                            user_images.append(
                                ChatImage(image_id=base_id, mime_type=base_mime, label="編集元画像")
                            )
                        if mask_file and mask_file.filename:
                            mask_bytes = mask_file.read()
                            mask_mime = mask_file.mimetype or "image/png"
                            mask_id = persist_image_bytes(raw_bytes=mask_bytes, mime_type=mask_mime)
                            mask_file.stream.seek(0)
                            user_images.append(
                                ChatImage(image_id=mask_id, mime_type=mask_mime, label="マスク画像")
                            )

                        user_text = f"メニュー: インペイント/アウトペイント編集（{edit_mode}）"
                        if edit_instruction:
                            user_text += f"\n指示: {edit_instruction}"
                        chat_history = append_chat_message(
                            chat_history,
                            build_user_message(text=user_text, images=user_images),
                        )

                        result = run_edit_generation(
                            base_file=base_file,
                            base_data=None,
                            mask_data=None,
                            mask_file=mask_file,
                            edit_mode=edit_mode,
                            edit_instruction=edit_instruction,
                        )
                    else:
                        rough_file = request.files.get("chat_rough_image")
                        color_instruction = request.form.get("chat_color_instruction", "")
                        pose_instruction = request.form.get("chat_pose_instruction", "")

                        user_images = []
                        if rough_file and rough_file.filename:
                            rough_bytes = rough_file.read()
                            rough_mime = rough_file.mimetype or "image/png"
                            rough_id = persist_image_bytes(raw_bytes=rough_bytes, mime_type=rough_mime)
                            rough_file.stream.seek(0)
                            user_images.append(ChatImage(image_id=rough_id, mime_type=rough_mime, label="ラフ"))

                        user_text = "メニュー: ラフ→仕上げ（色・ポーズ指示）"
                        if color_instruction:
                            user_text += f"\n色: {color_instruction}"
                        if pose_instruction:
                            user_text += f"\nポーズ: {pose_instruction}"
                        chat_history = append_chat_message(
                            chat_history,
                            build_user_message(text=user_text, images=user_images),
                        )

                        result = run_generation(
                            file=rough_file,
                            color_instruction=color_instruction,
                            pose_instruction=pose_instruction,
                            aspect_ratio_label=aspect_ratio_label,
                            resolution_label=resolution_label,
                        )

                    save_result_to_session(result)
                    image_data = result.image_data_uri
                    assistant_images = [
                        ChatImage(
                            image_id=result.image_id,
                            mime_type=result.mime_type,
                            label="生成結果",
                        )
                    ]
                    chat_history = append_chat_message(
                        chat_history,
                        build_assistant_message("画像生成が完了しました。", images=assistant_images),
                    )
                    flash("チャットから生成リクエストを送信しました。", "success")
                else:
                    message_text = (request.form.get("chat_message") or "").strip()
                    message_image = request.files.get("chat_image")
                    if not message_text and (message_image is None or message_image.filename == ""):
                        flash("テキストまたは画像を入力してください。", "error")
                    else:
                        images = []
                        if message_image and message_image.filename:
                            raw_bytes = message_image.read()
                            mime_type = message_image.mimetype or "image/png"
                            image_id = persist_image_bytes(raw_bytes=raw_bytes, mime_type=mime_type)
                            images.append(ChatImage(image_id=image_id, mime_type=mime_type, label="ユーザー画像"))
                            message_image.stream.seek(0)

                        user_text = message_text or "画像を送信しました。"
                        chat_history = append_chat_message(
                            chat_history,
                            build_user_message(text=user_text, images=images),
                        )
                        contents = build_chat_contents(chat_history)
                        response_text = generate_chat_response(contents=contents)
                        chat_history = append_chat_message(
                            chat_history,
                            build_assistant_message(response_text),
                        )
            else:
                aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
                resolution_label = request.form.get("resolution") or "auto"

                if current_mode == MODE_REFERENCE_STYLE_COLORIZE.id:
                    reference_file = request.files.get("reference_image")
                    rough_file = request.files.get("rough_image")
                    result = run_generation_with_reference(
                        reference_file=reference_file,
                        rough_file=rough_file,
                        aspect_ratio_label=aspect_ratio_label,
                        resolution_label=resolution_label,
                    )
                elif current_mode == MODE_INPAINT_OUTPAINT.id:
                    base_file = request.files.get("edit_base_image")
                    base_data = request.form.get("edit_base_data", "")
                    mask_data = request.form.get("edit_mask_data", "")
                    edit_mode = request.form.get("edit_mode", "inpaint")
                    edit_instruction = request.form.get("edit_instruction", "")
                    result = run_edit_generation(
                        base_file=base_file,
                        base_data=base_data,
                        mask_data=mask_data,
                        mask_file=None,
                        edit_mode=edit_mode,
                        edit_instruction=edit_instruction,
                    )
                else:
                    file = request.files.get("rough_image")
                    color_instruction = request.form.get("color_instruction", "")
                    pose_instruction = request.form.get("pose_instruction", "")
                    result = run_generation(
                        file=file,
                        color_instruction=color_instruction,
                        pose_instruction=pose_instruction,
                        aspect_ratio_label=aspect_ratio_label,
                        resolution_label=resolution_label,
                    )
        except GenerationError as exc:
            flash(str(exc), "error")
        except MissingApiKeyError:
            current_app.logger.error("Missing API key for image generation.")
            flash("APIキーが設定されていません。", "error")
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("Image generation failed: %s", exc)
            flash("画像生成に失敗しました。しばらくしてから再試行してください。", "error")
        else:
            if current_mode != MODE_CHAT_GUI.id:
                save_result_to_session(result)
                image_data = result.image_data_uri
                flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data = _restore_result()

    user_presets = _fetch_presets()
    presets_payload = [
        {
            "id": preset.id,
            "name": preset.name,
            "color": preset.color_instruction,
            "pose": preset.pose_instruction,
        }
        for preset in user_presets
    ]

    chat_payload = []
    for message in chat_history:
        image_payloads = []
        for image in message.images:
            data_uri = load_image_data_uri(image.image_id, image.mime_type)
            if not data_uri:
                continue
            image_payloads.append(
                {
                    "data_uri": data_uri,
                    "label": image.label,
                }
            )
        chat_payload.append(
            {
                "role": message.role,
                "text": message.text,
                "images": image_payloads,
            }
        )

    return render_template(
        "index.html",
        image_data=image_data,
        modes=ALL_MODES,
        current_mode=current_mode,
        aspect_ratio_options=ASPECT_RATIO_OPTIONS,
        resolution_options=RESOLUTION_OPTIONS,
        user_presets=user_presets,
        presets_payload=presets_payload,
        chat_history=chat_payload,
    )


@main_bp.route("/download")
@login_required
def download():
    image_path = load_image_path_from_session()
    if not image_path:
        abort(404)

    mime_type = load_mime_type_from_session()
    return send_file(
        image_path,
        mimetype=mime_type,
        as_attachment=True,
        download_name=f"generated_image{extension_for_mime_type(mime_type)}",
    )


@main_bp.route("/presets", methods=["POST"])
@login_required
def create_preset():
    """色とポーズの指示をプリセットとして保存する。"""

    mode = normalize_mode_id(request.form.get("mode"))
    name = (request.form.get("preset_name") or "").strip()
    color_instruction = (request.form.get("preset_color") or "").strip()
    pose_instruction = (request.form.get("preset_pose") or "").strip()

    if not name:
        flash("プリセット名を入力してください。", "error")
        return redirect(url_for("main.index", mode=mode))

    if len(name) > 80:
        flash("プリセット名は80文字以内にしてください。", "error")
        return redirect(url_for("main.index", mode=mode))

    if not color_instruction or not pose_instruction:
        flash("色とポーズの指示を両方入力してください。", "error")
        return redirect(url_for("main.index", mode=mode))

    if len(color_instruction) > 200 or len(pose_instruction) > 160:
        flash("文字数上限を超えています。入力内容を短くしてください。", "error")
        return redirect(url_for("main.index", mode=mode))

    preset = IllustrationPreset(
        user_id=current_user.id,
        name=name,
        color_instruction=color_instruction,
        pose_instruction=pose_instruction,
    )
    db.session.add(preset)
    db.session.commit()
    flash("プリセットを保存しました。", "success")
    return redirect(url_for("main.index", mode=mode))


@main_bp.route("/presets/delete", methods=["POST"])
@login_required
def delete_preset():
    """選択されたプリセットを削除する。"""

    mode = normalize_mode_id(request.form.get("mode"))
    preset_id = request.form.get("preset_id", type=int)
    if not preset_id:
        flash("削除するプリセットを選択してください。", "error")
        return redirect(url_for("main.index", mode=mode))

    preset = IllustrationPreset.query.filter_by(
        id=preset_id, user_id=current_user.id
    ).first()
    if not preset:
        flash("指定されたプリセットが見つかりません。", "error")
        return redirect(url_for("main.index", mode=mode))

    db.session.delete(preset)
    db.session.commit()
    flash("プリセットを削除しました。", "info")
    return redirect(url_for("main.index", mode=mode))
