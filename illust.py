from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Optional
import os
from google import genai
from google.genai import types
from PIL import Image

from dotenv import load_dotenv

# .env に記載したAPIキーなどの環境変数を読み込む
load_dotenv()

client = genai.Client()


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
    image_config_kwargs: dict[str, object] = {}
    if aspect_ratio:
        image_config_kwargs["aspect_ratio"] = aspect_ratio

    image_size = _map_resolution_to_image_size(resolution)
    if image_size:
        image_config_kwargs["image_size"] = image_size

    config_kwargs: dict[str, object] = {
        # テキストによる補足説明も返ってきてほしいので TEXT + IMAGE
        "response_modalities": ["TEXT", "IMAGE"],
    }
    if image_config_kwargs:
        config_kwargs["image_config"] = types.ImageConfig(**image_config_kwargs)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=[prompt, image],
        config=types.GenerateContentConfig(**config_kwargs),
    )

    image_bytes: Optional[bytes] = None
    mime_type: str = "image/png"

    for part in response.parts:
        # モデルが説明テキストを返すことがあるのでログに出す
        if getattr(part, "text", None):
            print(part.text)

        inline_data = getattr(part, "inline_data", None)
        if inline_data and getattr(inline_data, "data", None):
            image_bytes = inline_data.data
            # 可能ならレスポンス側の MIME タイプを尊重
            mime_type = getattr(inline_data, "mime_type", mime_type) or mime_type
            break

    if image_bytes is None:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    byte_stream = BytesIO(image_bytes)
    generated_image = Image.open(byte_stream)
    generated_image.load()

    # ここでファイル保存したければコメントを外す
    # generated_image.save("generated_image.png")

    return GeneratedImage(
        image=generated_image,
        raw_bytes=image_bytes,
        mime_type=mime_type,
        prompt=prompt,
    )
