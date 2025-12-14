from __future__ import annotations

import base64
from io import BytesIO
from typing import Optional

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from extensions import db
from models import IllustrationPreset
from services.generation_service import (
    GenerationError,
    load_result_from_session,
    run_generation,
    save_result_to_session,
)


main_bp = Blueprint("main", __name__)

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]


def _restore_result() -> tuple[Optional[str], Optional[str]]:
    """セッションに保存された結果から表示用データを復元する。"""

    existing = load_result_from_session()
    if not existing:
        return None, None
    return existing.image_data_uri, existing.prompt_text


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
    prompt_text: Optional[str] = None

    if request.method == "POST":
        file = request.files.get("rough_image")
        color_instruction = request.form.get("color_instruction", "")
        pose_instruction = request.form.get("pose_instruction", "")
        aspect_ratio_label = request.form.get("aspect_ratio") or "auto"
        resolution_label = request.form.get("resolution") or "auto"

        try:
            result = run_generation(
                file=file,
                color_instruction=color_instruction,
                pose_instruction=pose_instruction,
                aspect_ratio_label=aspect_ratio_label,
                resolution_label=resolution_label,
            )
        except GenerationError as exc:
            flash(str(exc), "error")
        except Exception as exc:  # noqa: BLE001
            flash(f"画像生成に失敗しました: {exc}", "error")
        else:
            save_result_to_session(result)
            image_data = result.image_data_uri
            prompt_text = result.prompt_text
            flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data, prompt_text = _restore_result()

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
        prompt_text=prompt_text,
        aspect_ratio_options=ASPECT_RATIO_OPTIONS,
        resolution_options=RESOLUTION_OPTIONS,
        user_presets=user_presets,
        presets_payload=presets_payload,
    )


@main_bp.route("/download")
@login_required
def download():
    existing = load_result_from_session()
    if not existing:
        abort(404)

    raw_bytes = base64.b64decode(existing.encoded_image)
    return send_file(
        BytesIO(raw_bytes),
        mimetype=existing.mime_type,
        as_attachment=True,
        download_name="generated_image.png",
    )


@main_bp.route("/presets", methods=["POST"])
@login_required
def create_preset():
    """色とポーズの指示をプリセットとして保存する。"""

    name = (request.form.get("preset_name") or "").strip()
    color_instruction = (request.form.get("preset_color") or "").strip()
    pose_instruction = (request.form.get("preset_pose") or "").strip()

    if not name:
        flash("プリセット名を入力してください。", "error")
        return redirect(url_for("main.index"))

    if len(name) > 80:
        flash("プリセット名は80文字以内にしてください。", "error")
        return redirect(url_for("main.index"))

    if not color_instruction or not pose_instruction:
        flash("色とポーズの指示を両方入力してください。", "error")
        return redirect(url_for("main.index"))

    if len(color_instruction) > 200 or len(pose_instruction) > 160:
        flash("文字数上限を超えています。入力内容を短くしてください。", "error")
        return redirect(url_for("main.index"))

    preset = IllustrationPreset(
        user_id=current_user.id,
        name=name,
        color_instruction=color_instruction,
        pose_instruction=pose_instruction,
    )
    db.session.add(preset)
    db.session.commit()
    flash("プリセットを保存しました。", "success")
    return redirect(url_for("main.index"))


@main_bp.route("/presets/delete", methods=["POST"])
@login_required
def delete_preset():
    """選択されたプリセットを削除する。"""

    preset_id = request.form.get("preset_id", type=int)
    if not preset_id:
        flash("削除するプリセットを選択してください。", "error")
        return redirect(url_for("main.index"))

    preset = IllustrationPreset.query.filter_by(
        id=preset_id, user_id=current_user.id
    ).first()
    if not preset:
        flash("指定されたプリセットが見つかりません。", "error")
        return redirect(url_for("main.index"))

    db.session.delete(preset)
    db.session.commit()
    flash("プリセットを削除しました。", "info")
    return redirect(url_for("main.index"))
