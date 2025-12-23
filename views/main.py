from __future__ import annotations

from typing import Optional

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from illust import MissingApiKeyError
from extensions import db
from models import IllustrationPreset
from services.generation_service import (
    GenerationError,
    extension_for_mime_type,
    load_image_path_from_session,
    load_mime_type_from_session,
    load_result_from_session,
    run_generation,
    run_generation_with_reference,
    run_edit_generation,
    save_result_to_session,
)
from services.modes import ALL_MODES, MODE_REFERENCE_STYLE_COLORIZE, MODE_INPAINT_OUTPAINT, normalize_mode_id


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

    if request.method == "POST":
        aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
        resolution_label = request.form.get("resolution") or "auto"

        try:
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
                mask_file = request.files.get("edit_mask_image")
                base_data = request.form.get("edit_base_data", "")
                mask_data = request.form.get("edit_mask_data", "")
                edit_mode = request.form.get("edit_mode", "inpaint")
                edit_instruction = request.form.get("edit_instruction", "")
                result = run_edit_generation(
                    base_file=base_file,
                    mask_file=mask_file,
                    base_data=base_data,
                    mask_data=mask_data,
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

    return render_template(
        "index.html",
        image_data=image_data,
        modes=ALL_MODES,
        current_mode=current_mode,
        aspect_ratio_options=ASPECT_RATIO_OPTIONS,
        resolution_options=RESOLUTION_OPTIONS,
        user_presets=user_presets,
        presets_payload=presets_payload,
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
