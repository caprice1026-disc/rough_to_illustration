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
from services.modes import (
    ALL_MODES,
    MODE_CHAT,
    MODE_INPAINT_OUTPAINT,
    MODE_REFERENCE_STYLE_COLORIZE,
    MODE_ROUGH_WITH_INSTRUCTIONS,
    normalize_mode_id,
)


main_bp = Blueprint("main", __name__)

ASPECT_RATIO_OPTIONS = ["auto", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["auto", "1K", "2K", "4K"]
MODE_ROUTE_MAP = {
    MODE_ROUGH_WITH_INSTRUCTIONS.id: "main.generate_rough",
    MODE_REFERENCE_STYLE_COLORIZE.id: "main.generate_reference",
    MODE_INPAINT_OUTPAINT.id: "main.generate_edit",
    MODE_CHAT.id: "chat.index",
}


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

def _build_presets_payload(user_presets: list[IllustrationPreset]) -> list[dict[str, str]]:
    return [
        {
            "id": preset.id,
            "name": preset.name,
            "color": preset.color_instruction,
            "pose": preset.pose_instruction,
        }
        for preset in user_presets
    ]


def _mode_url_map() -> dict[str, str]:
    return {mode_id: url_for(endpoint) for mode_id, endpoint in MODE_ROUTE_MAP.items()}


def _resolve_mode_endpoint(mode_id: Optional[str]) -> str:
    normalized = normalize_mode_id(mode_id)
    return MODE_ROUTE_MAP.get(normalized, MODE_ROUTE_MAP[MODE_ROUGH_WITH_INSTRUCTIONS.id])


def _redirect_to_mode(mode_id: Optional[str]):
    return redirect(url_for(_resolve_mode_endpoint(mode_id)))


def _build_common_context(current_mode: str, image_data: Optional[str]) -> dict[str, object]:
    user_presets = _fetch_presets()
    return {
        "image_data": image_data,
        "modes": ALL_MODES,
        "current_mode": current_mode,
        "aspect_ratio_options": ASPECT_RATIO_OPTIONS,
        "resolution_options": RESOLUTION_OPTIONS,
        "user_presets": user_presets,
        "presets_payload": _build_presets_payload(user_presets),
        "mode_routes": _mode_url_map(),
    }


def _handle_generation_error(exc: Exception) -> None:
    if isinstance(exc, GenerationError):
        flash(str(exc), "error")
        return
    if isinstance(exc, MissingApiKeyError):
        current_app.logger.error("Missing API key for image generation.")
        flash("APIキーが設定されていません。", "error")
        return
    current_app.logger.exception("Image generation failed: %s", exc)
    flash("画像生成に失敗しました。しばらくしてから再試行してください。", "error")


@main_bp.route("/", methods=["GET"])
@login_required
def index():
    return _redirect_to_mode(MODE_ROUGH_WITH_INSTRUCTIONS.id)


@main_bp.route("/generate/rough", methods=["GET", "POST"])
@login_required
def generate_rough():
    image_data: Optional[str] = None
    current_mode = MODE_ROUGH_WITH_INSTRUCTIONS.id

    if request.method == "POST":
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
        except Exception as exc:  # noqa: BLE001
            _handle_generation_error(exc)
        else:
            save_result_to_session(result)
            image_data = result.image_data_uri
            flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data = _restore_result()

    context = _build_common_context(current_mode, image_data)
    context.update(
        {
            "hero_title": "ラフ絵を高品質イラストへ",
            "hero_subtitle": "ラフ1枚と色・ポーズ指示で、Gemini に仕上げを依頼します。プレビューで確認しながら安心して送信できます。",
            "submit_label": "イラスト生成をリクエスト",
            "preset_detail": "色とポーズの組み合わせを保存して再利用できます。",
            "preset_save_hint": "下の色・ポーズ欄の現在の入力を保存します。",
            "empty_hint": "ラフスケッチをアップロードして「イラスト生成」を押すと、ここにプレビューが表示されます。",
        }
    )
    return render_template("modes/rough.html", **context)


@main_bp.route("/generate/reference", methods=["GET", "POST"])
@login_required
def generate_reference():
    image_data: Optional[str] = None
    current_mode = MODE_REFERENCE_STYLE_COLORIZE.id

    if request.method == "POST":
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
        except Exception as exc:  # noqa: BLE001
            _handle_generation_error(exc)
        else:
            save_result_to_session(result)
            image_data = result.image_data_uri
            flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data = _restore_result()

    context = _build_common_context(current_mode, image_data)
    context.update(
        {
            "hero_title": "完成絵の絵柄でラフを着色",
            "hero_subtitle": "完成済みイラストとラフスケッチの2枚を使って、参照絵柄に沿った仕上げを依頼します。",
            "submit_label": "参照して着色をリクエスト",
            "preset_detail": "追加指示のテンプレートを保存して再利用できます。",
            "preset_save_hint": "下の追加指示の現在の入力を保存します。",
            "empty_hint": "参考（完成）画像とラフスケッチをアップロードして「参照して着色」を押すと、ここにプレビューが表示されます。",
        }
    )
    return render_template("modes/reference.html", **context)


@main_bp.route("/generate/edit", methods=["GET", "POST"])
@login_required
def generate_edit():
    image_data: Optional[str] = None
    current_mode = MODE_INPAINT_OUTPAINT.id

    if request.method == "POST":
        base_file = request.files.get("edit_base_image")
        base_data = request.form.get("edit_base_data", "")
        mask_data = request.form.get("edit_mask_data", "")
        edit_mode = request.form.get("edit_mode", "inpaint")
        edit_instruction = request.form.get("edit_instruction", "")

        try:
            result = run_edit_generation(
                base_file=base_file,
                base_data=base_data,
                mask_data=mask_data,
                edit_mode=edit_mode,
                edit_instruction=edit_instruction,
            )
        except Exception as exc:  # noqa: BLE001
            _handle_generation_error(exc)
        else:
            save_result_to_session(result)
            image_data = result.image_data_uri
            flash("イラストの生成が完了しました。", "success")

    if not image_data:
        image_data = _restore_result()

    context = _build_common_context(current_mode, image_data)
    context.update(
        {
            "hero_title": "インペイント/アウトペイント編集",
            "hero_subtitle": "編集対象画像とマスクを使い、指定領域だけを修正または拡張します。",
            "submit_label": "編集をリクエスト",
            "preset_detail": "編集指示のテンプレートを保存して再利用できます。",
            "preset_save_hint": "下の追加指示の現在の入力を保存します。",
            "empty_hint": "編集対象画像をアップロードしてマスクを描き、「編集をリクエスト」を押すと、ここにプレビューが表示されます。",
        }
    )
    return render_template("modes/edit.html", **context)


@main_bp.route("/modes")
@login_required
def mode_select():
    """生成モードの選択画面を表示する。"""

    current_mode = normalize_mode_id(request.args.get("mode"))
    return render_template(
        "mode_select.html",
        modes=ALL_MODES,
        current_mode=current_mode,
        mode_routes=_mode_url_map(),
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
    """各モードの指示をプリセットとして保存する。"""

    mode = normalize_mode_id(request.form.get("mode"))
    name = (request.form.get("preset_name") or "").strip()
    color_instruction = (request.form.get("preset_color") or "").strip()
    pose_instruction = (request.form.get("preset_pose") or "").strip()

    if not name:
        flash("プリセット名を入力してください。", "error")
        return _redirect_to_mode(mode)

    if len(name) > 80:
        flash("プリセット名は80文字以内にしてください。", "error")
        return _redirect_to_mode(mode)

    if mode in {MODE_REFERENCE_STYLE_COLORIZE.id, MODE_INPAINT_OUTPAINT.id}:
        if not color_instruction:
            flash("追加指示を入力してください。", "error")
            return _redirect_to_mode(mode)
        pose_instruction = ""
        if len(color_instruction) > 1000:
            flash("文字数上限を超えています。入力内容を短くしてください。", "error")
            return _redirect_to_mode(mode)
    else:
        if not color_instruction or not pose_instruction:
            flash("色とポーズの指示を両方入力してください。", "error")
            return _redirect_to_mode(mode)

        if len(color_instruction) > 200 or len(pose_instruction) > 160:
            flash("文字数上限を超えています。入力内容を短くしてください。", "error")
            return _redirect_to_mode(mode)

    preset = IllustrationPreset(
        user_id=current_user.id,
        name=name,
        color_instruction=color_instruction,
        pose_instruction=pose_instruction,
    )
    db.session.add(preset)
    db.session.commit()
    flash("プリセットを保存しました。", "success")
    return _redirect_to_mode(mode)


@main_bp.route("/presets/delete", methods=["POST"])
@login_required
def delete_preset():
    """選択されたプリセットを削除する。"""

    mode = normalize_mode_id(request.form.get("mode"))
    preset_id = request.form.get("preset_id", type=int)
    if not preset_id:
        flash("削除するプリセットを選択してください。", "error")
        return _redirect_to_mode(mode)

    preset = IllustrationPreset.query.filter_by(
        id=preset_id, user_id=current_user.id
    ).first()
    if not preset:
        flash("指定されたプリセットが見つかりません。", "error")
        return _redirect_to_mode(mode)

    db.session.delete(preset)
    db.session.commit()
    flash("プリセットを削除しました。", "info")
    return _redirect_to_mode(mode)
