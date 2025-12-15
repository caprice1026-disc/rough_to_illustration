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

from illust import generate_image
from services.prompt_builder import build_prompt


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


def decode_uploaded_image(file: Optional[FileStorage]) -> Image.Image:
    """アップロードされた画像ファイルをPIL Imageとして読み込む。"""

    if file is None or file.filename == "":
        raise GenerationError("ラフ絵ファイルを選択してください。")

    try:
        raw_bytes = file.read()
        image = Image.open(BytesIO(raw_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise GenerationError(f"画像の読み込みに失敗しました: {exc}") from exc

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

    image = decode_uploaded_image(file)
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
