from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from typing import Any, Optional

from google import genai
from google.genai import types
from PIL import Image

from dotenv import load_dotenv

# .env に記載したAPIキーなどの環境変数を読み込む
load_dotenv()

DEFAULT_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

logger = logging.getLogger(__name__)


class MissingApiKeyError(RuntimeError):
    """APIキーが設定されていない場合の例外。"""


@lru_cache(maxsize=1)
def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise MissingApiKeyError("APIキーが設定されていません。")
    return genai.Client(api_key=api_key)


@dataclass
class GeneratedImage:
    """生成画像のメタデータと利用しやすい表現をまとめたコンテナ。"""

    image: Image.Image
    raw_bytes: bytes
    mime_type: str
    prompt: str


def _map_resolution_to_image_size(resolution: Optional[str]) -> Optional[str]:
    """
    UI の解像度指定を、Gemini 3 Pro Image の image_size に変換する。

    - "1K", "2K", "4K" はそのまま
    - "720p", "1080p" は便宜的に "1K" に丸める
    - それ以外は None（デフォルト解像度）
    """
    if not resolution:
        return None

    normalized = resolution.strip().upper()
    if normalized in {"1K"}:
        return "1K"
    if normalized in {"2K"}:
        return "2K"
    if normalized in {"4K"}:
        return "4K"
    if normalized in {"720P"}:
        return "1K"
    if normalized in {"1080P", "1080"}:
        return "1K"
    return None


def generate_image(
    prompt: str,
    image: Image.Image,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
) -> GeneratedImage:
    """
    プロンプトと画像を使って Gemini 3 Pro Image Preview を叩く関数。

    Args:
        prompt: ユーザー指定の説明文（色指定などを含む）
        image: ラフ絵 (PIL Image)。
        aspect_ratio: "1:1" / "4:5" / "16:9" など。None の場合はモデル任せ。
        resolution: "1K" / "2K" / "4K" または UI ラベル ("720p" / "1080p" / "2K")。
    """

    # 公式ドキュメントに合わせて image_config で制御する 
    image_config_kwargs: dict[str, Any] = {}
    if aspect_ratio:
        image_config_kwargs["aspect_ratio"] = aspect_ratio

    image_size = _map_resolution_to_image_size(resolution)
    if image_size:
        image_config_kwargs["image_size"] = image_size

    config_kwargs: dict[str, Any] = {
        # テキストによる補足説明も返ってきてほしいので TEXT + IMAGE
        "response_modalities": ["TEXT", "IMAGE"],
    }
    if image_config_kwargs:
        config_kwargs["image_config"] = types.ImageConfig(**image_config_kwargs)

    response = _client().models.generate_content(
        model=DEFAULT_IMAGE_MODEL,
        contents=[prompt, image],
        config=types.GenerateContentConfig(**config_kwargs),
    )

    image_bytes: Optional[bytes] = None
    mime_type: str = "image/png"

    for part in response.parts:
        # モデルが説明テキストを返すことがあるのでログに出す
        if getattr(part, "text", None):
            logger.debug("Gemini response text: %s", part.text)

        inline_data = getattr(part, "inline_data", None)
        if inline_data and getattr(inline_data, "data", None):
            image_bytes = inline_data.data
            # 可能ならレスポンス側の MIME タイプを尊重
            mime_type = getattr(inline_data, "mime_type", mime_type) or mime_type
            break

    if image_bytes is None:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    byte_stream = BytesIO(image_bytes)
    generated_image: Image.Image = Image.open(byte_stream)
    generated_image.load()

    # ここでファイル保存したければコメントを外す
    # generated_image.save("generated_image.png")

    return GeneratedImage(
        image=generated_image,
        raw_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
    )


def generate_image_with_contents(
    *,
    contents: list[object],
    prompt_for_record: str,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
) -> GeneratedImage:
    if not contents:
        raise ValueError("contents must not be empty")

    image_config_kwargs: dict[str, Any] = {}
    if aspect_ratio:
        image_config_kwargs["aspect_ratio"] = aspect_ratio

    image_size = _map_resolution_to_image_size(resolution)
    if image_size:
        image_config_kwargs["image_size"] = image_size

    config_kwargs: dict[str, Any] = {
        "response_modalities": ["TEXT", "IMAGE"],
    }
    if image_config_kwargs:
        config_kwargs["image_config"] = types.ImageConfig(**image_config_kwargs)

    response = _client().models.generate_content(
        model=DEFAULT_IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(**config_kwargs),
    )

    image_bytes: Optional[bytes] = None
    mime_type: str = "image/png"

    for part in response.parts:
        if getattr(part, "text", None):
            logger.debug("Gemini response text: %s", part.text)

        inline_data = getattr(part, "inline_data", None)
        if inline_data and getattr(inline_data, "data", None):
            image_bytes = inline_data.data
            mime_type = getattr(inline_data, "mime_type", mime_type) or mime_type
            break

    if image_bytes is None:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    byte_stream = BytesIO(image_bytes)
    generated_image: Image.Image = Image.open(byte_stream)
    generated_image.load()

    return GeneratedImage(
        image=generated_image,
        raw_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt_for_record,
    )


def generate_image_with_images(
    prompt: str,
    images: list[Image.Image],
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
) -> GeneratedImage:
    """
    プロンプトと複数画像を使って Gemini 3 Pro Image Preview を叩く関数。

    Args:
        prompt: 指示文。
        images: 入力画像（1枚以上）。順序もモデルの解釈に影響するため、意図した順に渡す。
        aspect_ratio: "1:1" / "4:5" / "16:9" など。None の場合はモデル任せ。
        resolution: "1K" / "2K" / "4K" または UI ラベル ("720p" / "1080p" / "2K")。
    """

    if not images:
        raise ValueError("images must not be empty")

    return generate_image_with_contents(
        contents=[prompt, *images],
        prompt_for_record=prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
    )



def _pil_to_types_image(image: Image.Image, *, mime_type: str = "image/png") -> types.Image:
    buffer = BytesIO()
    format_map = {
        "image/png": "PNG",
        "image/jpeg": "JPEG",
        "image/jpg": "JPEG",
    }
    image.save(buffer, format=format_map.get(mime_type, "PNG"))
    return types.Image(image_bytes=buffer.getvalue(), mime_type=mime_type)


def edit_image_with_mask(
    *,
    prompt: str,
    base_image: Image.Image,
    mask_image: Image.Image,
    edit_mode: str,
    aspect_ratio: Optional[str] = None,
) -> GeneratedImage:
    """
    マスク画像を用いてインペイント/アウトペイントを行う。

    Args:
        prompt: 編集指示テキスト。
        base_image: ベース画像。
        mask_image: マスク画像（非ゼロが編集対象）。
        edit_mode: "inpaint" または "outpaint"。
        aspect_ratio: 出力のアスペクト比（指定がある場合のみ）。
    """

    if edit_mode == "outpaint":
        edit_mode_value = types.EditMode.EDIT_MODE_OUTPAINT
    else:
        edit_mode_value = types.EditMode.EDIT_MODE_INPAINT_INSERTION

    raw_ref = types.RawReferenceImage(
        reference_id=1,
        reference_image=_pil_to_types_image(base_image),
    )
    mask_ref = types.MaskReferenceImage(
        reference_id=2,
        reference_image=_pil_to_types_image(mask_image),
        config=types.MaskReferenceConfig(mask_mode="MASK_MODE_USER_PROVIDED"),
    )

    config_kwargs: dict[str, Any] = {
        "edit_mode": edit_mode_value,
        "number_of_images": 1,
        "output_mime_type": "image/png",
    }
    if aspect_ratio:
        config_kwargs["aspect_ratio"] = aspect_ratio

    response = _client().models.edit_image(
        model=DEFAULT_IMAGE_MODEL,
        prompt=prompt,
        reference_images=[raw_ref, mask_ref],
        config=types.EditImageConfig(**config_kwargs),
    )

    if not response or not response.generated_images:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    chosen = None
    for generated in response.generated_images:
        if generated.image and generated.image.image_bytes:
            chosen = generated
            break

    if not chosen or not chosen.image or not chosen.image.image_bytes:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    image_bytes = chosen.image.image_bytes
    mime_type = chosen.image.mime_type or "image/png"
    generated_image = Image.open(BytesIO(image_bytes))
    generated_image.load()

    return GeneratedImage(
        image=generated_image,
        raw_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
    )
