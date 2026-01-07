from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import uuid4

from flask import current_app, session
from PIL import Image, UnidentifiedImageError
from werkzeug.datastructures import FileStorage

from illust import generate_image, generate_image_with_contents, edit_image_with_mask
from services.prompt_builder import build_prompt, build_reference_style_colorize_prompt, build_edit_prompt


ALLOWED_IMAGE_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg"}
ALLOWED_IMAGE_MIME_ALIASES = {"image/jpg": "image/jpeg"}
ALLOWED_IMAGE_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
ALLOWED_IMAGE_LABEL = "PNG/JPEG"


def _normalize_mime_type(mime_type: Optional[str]) -> Optional[str]:
    if not mime_type:
        return None
    normalized = mime_type.split(";", 1)[0].strip().lower()
    return ALLOWED_IMAGE_MIME_ALIASES.get(normalized, normalized)


def _normalize_extension(filename: Optional[str]) -> Optional[str]:
    if not filename:
        return None
    suffix = Path(filename).suffix.lower()
    return suffix or None


def extension_for_mime_type(mime_type: str) -> str:
    normalized = _normalize_mime_type(mime_type) or mime_type
    if normalized == "image/png":
        return ".png"
    if normalized in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    return ".png"


def _limit_value(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return value if value > 0 else None


def _apply_pil_max_image_pixels() -> Optional[int]:
    max_pixels = _limit_value(current_app.config.get("MAX_IMAGE_PIXELS"))
    Image.MAX_IMAGE_PIXELS = max_pixels
    return max_pixels


def _validate_upload_metadata(
    *,
    label: str,
    extension: Optional[str],
    mime_type: Optional[str],
    require_extension: bool,
) -> None:
    allowed_mimes = set(ALLOWED_IMAGE_FORMATS.values())
    if require_extension:
        if not extension or extension not in ALLOWED_IMAGE_EXTENSIONS:
            raise GenerationError(f"{label}は{ALLOWED_IMAGE_LABEL}のみ対応しています。")
    elif extension and extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise GenerationError(f"{label}は{ALLOWED_IMAGE_LABEL}のみ対応しています。")

    if mime_type and mime_type not in allowed_mimes:
        raise GenerationError(f"{label}は{ALLOWED_IMAGE_LABEL}のみ対応しています。")

    if extension and mime_type:
        expected = ALLOWED_IMAGE_EXTENSIONS.get(extension)
        if expected and expected != mime_type:
            raise GenerationError(f"{label}のMIMEタイプと拡張子が一致しません。{ALLOWED_IMAGE_LABEL}を選択してください。")


def _mime_type_for_format(format_name: Optional[str]) -> Optional[str]:
    if not format_name:
        return None
    return ALLOWED_IMAGE_FORMATS.get(format_name.upper())


def _validate_format_consistency(
    *,
    label: str,
    format_mime: str,
    extension: Optional[str],
    mime_type: Optional[str],
) -> None:
    if mime_type and mime_type != format_mime:
        raise GenerationError(f"{label}のMIMEタイプと画像内容が一致しません。{ALLOWED_IMAGE_LABEL}を選択してください。")
    if extension:
        expected = ALLOWED_IMAGE_EXTENSIONS.get(extension)
        if expected and expected != format_mime:
            raise GenerationError(f"{label}の拡張子と画像内容が一致しません。{ALLOWED_IMAGE_LABEL}を選択してください。")


def _validate_image_dimensions(image: Image.Image, *, label: str) -> None:
    width, height = image.size
    max_width = _limit_value(current_app.config.get("MAX_IMAGE_WIDTH"))
    max_height = _limit_value(current_app.config.get("MAX_IMAGE_HEIGHT"))
    max_pixels = _limit_value(current_app.config.get("MAX_IMAGE_PIXELS"))

    if (max_width and width > max_width) or (max_height and height > max_height):
        parts = []
        if max_width:
            parts.append(f"最大幅{max_width}px")
        if max_height:
            parts.append(f"最大高さ{max_height}px")
        limit_text = "、".join(parts) if parts else "上限"
        raise GenerationError(f"{label}のサイズが上限を超えています。{limit_text}までです。")

    if max_pixels and width * height > max_pixels:
        raise GenerationError(f"{label}のピクセル数が上限({max_pixels}ピクセル)を超えています。")


def _pixel_limit_error(label: str, max_pixels: Optional[int]) -> str:
    if max_pixels:
        return f"{label}のピクセル数が上限({max_pixels}ピクセル)を超えています。"
    return f"{label}のピクセル数が上限を超えています。"


def read_uploaded_bytes(
    file: Optional[FileStorage],
    *,
    label: str = "画像",
    reset_stream: bool = False,
) -> tuple[bytes, Optional[str], Optional[str]]:
    if file is None or file.filename == "":
        raise GenerationError(f"{label}を選択してください。")
    raw_bytes = file.read()
    if reset_stream:
        try:
            file.stream.seek(0)
        except Exception:  # noqa: BLE001
            pass
    return raw_bytes, file.filename, file.mimetype


def decode_image_bytes(
    raw_bytes: bytes,
    *,
    label: str = "画像",
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
    convert_to_rgb: bool = False,
) -> Image.Image:
    if not raw_bytes:
        raise GenerationError(f"{label}が空です。")

    extension = _normalize_extension(filename)
    normalized_mime = _normalize_mime_type(mime_type)
    _validate_upload_metadata(
        label=label,
        extension=extension,
        mime_type=normalized_mime,
        require_extension=filename is not None,
    )

    max_pixels = _apply_pil_max_image_pixels()
    try:
        image = Image.open(BytesIO(raw_bytes))
        format_mime = _mime_type_for_format(image.format)
        if not format_mime:
            raise GenerationError(f"{label}は{ALLOWED_IMAGE_LABEL}のみ対応しています。")
        _validate_format_consistency(
            label=label,
            format_mime=format_mime,
            extension=extension,
            mime_type=normalized_mime,
        )
        _validate_image_dimensions(image, label=label)
        if convert_to_rgb:
            image = image.convert("RGB")
        else:
            image.load()
    except Image.DecompressionBombError as exc:
        raise GenerationError(_pixel_limit_error(label, max_pixels)) from exc
    except GenerationError:
        raise
    except UnidentifiedImageError as exc:
        current_app.logger.exception("Failed to decode image (%s): %s", label, exc)
        raise GenerationError(f"画像の読み込みに失敗しました。{ALLOWED_IMAGE_LABEL}を確認してください。") from exc
    except Exception as exc:  # noqa: BLE001
        current_app.logger.exception("Failed to decode image (%s): %s", label, exc)
        raise GenerationError(f"画像の読み込みに失敗しました。{ALLOWED_IMAGE_LABEL}を確認してください。") from exc

    return image


def mime_type_for_image(image: Image.Image) -> str:
    format_mime = _mime_type_for_format(image.format)
    if not format_mime:
        raise GenerationError(f"画像形式が{ALLOWED_IMAGE_LABEL}ではありません。")
    return format_mime


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

    raw_bytes, filename, mime_type = read_uploaded_bytes(file, label=label)
    return decode_image_bytes(
        raw_bytes,
        label=label,
        filename=filename,
        mime_type=mime_type,
        convert_to_rgb=True,
    )


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

    raw_bytes, filename, mime_type = read_uploaded_bytes(file, label=label)
    return decode_image_bytes(
        raw_bytes,
        label=label,
        filename=filename,
        mime_type=mime_type,
        convert_to_rgb=False,
    )


def decode_data_url_image(data_url: str, *, label: str = "画像") -> Image.Image:
    """Data URL 形式の画像を PIL Image として読み込む。"""

    if not data_url:
        raise GenerationError(f"{label}が見つかりません。")

    if "," not in data_url:
        raise GenerationError(f"{label}の形式が不正です。")

    header, encoded = data_url.split(",", 1)
    if not header.startswith("data:"):
        raise GenerationError(f"{label}の形式が不正です。")

    header_parts = header[5:].split(";")
    mime_type = _normalize_mime_type(header_parts[0]) if header_parts else None
    if not mime_type or "base64" not in header_parts[1:]:
        raise GenerationError(f"{label}の形式が不正です。")

    try:
        raw_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise GenerationError(f"{label}の形式が不正です。") from exc

    return decode_image_bytes(raw_bytes, label=label, mime_type=mime_type, convert_to_rgb=False)


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
    mask_file: Optional[FileStorage] = None,
    mask_data: Optional[str],
    edit_mode: str,
    edit_instruction: str,
) -> GenerationResult:
    """編集モード用の画像生成を行う。"""

    if base_data:
        base_image = decode_data_url_image(base_data, label="編集元画像")
    else:
        base_image = decode_uploaded_image_raw(base_file, label="編集元画像")

    if mask_data:
        mask_image = decode_data_url_image(mask_data, label="マスク画像")
    elif mask_file:
        mask_image = decode_uploaded_image_raw(mask_file, label="マスク画像")
    else:
        raise GenerationError("マスク画像を用意してください。")

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
