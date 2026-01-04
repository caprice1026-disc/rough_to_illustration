from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

from flask import current_app, session
from PIL import Image
from werkzeug.datastructures import FileStorage

from illust import generate_image, generate_image_with_contents, edit_image_with_mask
from services.prompt_builder import build_prompt, build_reference_style_colorize_prompt, build_edit_prompt


def extension_for_mime_type(mime_type: str) -> str:
    if mime_type == "image/png":
        return ".png"
    if mime_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    return ".png"


def _generated_images_dir() -> Path:
    base = Path(current_app.instance_path) / "generated_images"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _generated_image_path(image_id: str) -> Path:
    safe_name = Path(image_id).name
    return _generated_images_dir() / safe_name


def _persist_generated_image(*, raw_bytes: bytes, mime_type: str) -> str:
    image_id = f"{uuid4().hex}{extension_for_mime_type(mime_type)}"
    path = _generated_image_path(image_id)
    path.write_bytes(raw_bytes)
    return image_id


def _delete_generated_image(image_id: Optional[str]) -> None:
    if not image_id:
        return
    path = _generated_image_path(image_id)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


@dataclass
class GenerationResult:
    """生成結果をフロントエンドで扱いやすい形にまとめたデータクラス。"""

    image_data_uri: str
    mime_type: str
    image_id: str


class GenerationError(ValueError):
    """入力バリデーションや前処理で発生した例外。"""


def normalize_optional(label: Optional[str]) -> Optional[str]:
    """フォームの「auto」をNoneに変換してAPIに渡す形へ揃える。"""

    if not label or label == "auto":
        return None
    return label


def decode_uploaded_image(file: Optional[FileStorage], *, label: str = "画像") -> Image.Image:
    """アップロードされた画像ファイルを PIL Image として読み込む。"""

    if file is None or file.filename == "":
        raise GenerationError(f"{label}を選択してください。")

    try:
        raw_bytes = file.read()
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to decode uploaded image (%s): %s", label, exc)
        raise GenerationError("画像の読み込みに失敗しました。PNG/JPG/JPEG を確認してください。") from exc

    return image


def run_generation(
    *,
    file: Optional[FileStorage],
    color_instruction: str,
    pose_instruction: str,
    aspect_ratio_label: Optional[str],
    resolution_label: Optional[str],
) -> GenerationResult:
    """入力からプロンプトを作成し、画像生成APIを呼び出して結果を返す。"""

    image = decode_uploaded_image(file, label="ラフ絵")
    aspect_ratio = normalize_optional(aspect_ratio_label)
    resolution = normalize_optional(resolution_label)
    prompt = build_prompt(color_instruction, pose_instruction)

    generated = generate_image(
        prompt=prompt,
        image=image,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )

    image_id = _persist_generated_image(
        raw_bytes=generated.raw_bytes,
        mime_type=generated.mime_type,
    )
    encoded = base64.b64encode(generated.raw_bytes).decode("utf-8")
    return GenerationResult(
        image_data_uri=f"data:{generated.mime_type};base64,{encoded}",
        mime_type=generated.mime_type,
        image_id=image_id,
    )


def run_generation_with_reference(
    *,
    reference_file: Optional[FileStorage],
    rough_file: Optional[FileStorage],
    reference_instruction: str,
    aspect_ratio_label: Optional[str],
    resolution_label: Optional[str],
) -> GenerationResult:
    """完成絵(参照)＋ラフ(対象)の2枚入力で画像生成APIを呼び出して結果を返す。"""

    reference_image = decode_uploaded_image(reference_file, label="参考（完成）画像")
    rough_image = decode_uploaded_image(rough_file, label="ラフスケッチ")
    aspect_ratio = normalize_optional(aspect_ratio_label)
    resolution = normalize_optional(resolution_label)
    prompt = build_reference_style_colorize_prompt(reference_instruction)

    contents = [
        "これから2枚の画像を渡します。1枚目は編集対象のラフスケッチです。",
        rough_image,
        "次に2枚目を渡します。2枚目は画風・質感・陰影・彩度レンジの参照となる完成済みイラストです。",
        reference_image,
        prompt,
    ]
    generated = generate_image_with_contents(
        contents=contents,
        prompt_for_record=prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )

    image_id = _persist_generated_image(
        raw_bytes=generated.raw_bytes,
        mime_type=generated.mime_type,
    )
    encoded = base64.b64encode(generated.raw_bytes).decode("utf-8")
    return GenerationResult(
        image_data_uri=f"data:{generated.mime_type};base64,{encoded}",
        mime_type=generated.mime_type,
        image_id=image_id,
    )


def save_result_to_session(result: GenerationResult) -> None:
    """生成結果をセッションへ保存して再描画時に利用できるようにする。"""

    previous_id = session.get("generated_image_id")
    _delete_generated_image(previous_id)

    session.pop("generated_image", None)
    session.pop("generated_prompt", None)
    session["generated_mime"] = result.mime_type
    session["generated_image_id"] = result.image_id


def load_result_from_session() -> Optional[GenerationResult]:
    """セッションに保存された生成結果を復元する。"""

    image_id = session.get("generated_image_id")
    if not image_id:
        return None

    path = _generated_image_path(image_id)
    if not path.exists():
        session.pop("generated_image_id", None)
        return None

    mime_type = session.get("generated_mime", "image/png")
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return GenerationResult(
        image_data_uri=f"data:{mime_type};base64,{encoded}",
        mime_type=mime_type,
        image_id=image_id,
    )


def load_image_path_from_session() -> Optional[Path]:
    image_id = session.get("generated_image_id")
    if not image_id:
        return None
    path = _generated_image_path(image_id)
    if not path.exists():
        session.pop("generated_image_id", None)
        return None
    return path


def load_mime_type_from_session() -> str:
    return session.get("generated_mime", "image/png")



def decode_uploaded_image_raw(file: Optional[FileStorage], *, label: str = "画像") -> Image.Image:
    """アップロードされた画像ファイルを変換せずに PIL Image として読み込む。"""

    if file is None or file.filename == "":
        raise GenerationError(f"{label}を選択してください。")

    try:
        raw_bytes = file.read()
        image = Image.open(BytesIO(raw_bytes))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to decode uploaded image (%s): %s", label, exc)
        raise GenerationError("画像の読み込みに失敗しました。PNG/JPG/JPEG を確認してください。") from exc

    return image


def decode_data_url_image(data_url: str, *, label: str = "画像") -> Image.Image:
    """Data URL 形式の画像を PIL Image として読み込む。"""

    if not data_url:
        raise GenerationError(f"{label}が見つかりません。")

    if "," not in data_url:
        raise GenerationError(f"{label}の形式が不正です。")

    _, encoded = data_url.split(",", 1)
    try:
        raw_bytes = base64.b64decode(encoded)
        image = Image.open(BytesIO(raw_bytes))
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to decode data URL image (%s): %s", label, exc)
        raise GenerationError("画像の読み込みに失敗しました。") from exc

    return image


def normalize_mask_image(mask_image: Image.Image) -> Image.Image:
    """マスク画像をグレースケールに正規化する。"""

    return mask_image.convert("L")


def ensure_rgb(image: Image.Image) -> Image.Image:
    """RGBA画像を白背景で合成してRGBに変換する。"""

    if image.mode == "RGB":
        return image
    if image.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        return background
    return image.convert("RGB")


def run_edit_generation(
    *,
    base_file: Optional[FileStorage],
    base_data: Optional[str],
    mask_data: Optional[str],
    edit_mode: str,
    edit_instruction: str,
) -> GenerationResult:
    """編集モード用の画像生成を行う。"""

    if base_data:
        base_image = decode_data_url_image(base_data, label="編集元画像")
    else:
        base_image = decode_uploaded_image_raw(base_file, label="編集元画像")

    if not mask_data:
        raise GenerationError("マスク画像を用意してください。エディタで描画して適用してください。")
    mask_image = decode_data_url_image(mask_data, label="マスク画像")

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

    image_id = _persist_generated_image(
        raw_bytes=generated.raw_bytes,
        mime_type=generated.mime_type,
    )
    encoded = base64.b64encode(generated.raw_bytes).decode("utf-8")
    return GenerationResult(
        image_data_uri=f"data:{generated.mime_type};base64,{encoded}",
        mime_type=generated.mime_type,
        image_id=image_id,
    )
