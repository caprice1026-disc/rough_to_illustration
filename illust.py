from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()


# クラスとして定義する必要があるかと言われると微妙
@dataclass
class GeneratedImage:
    """生成画像のメタデータと利用しやすい表現をまとめたコンテナ。"""

    image: Image.Image
    raw_bytes: bytes
    mime_type: str
    prompt: str


'''
この関数いらない。解像度はパラメーターとして直接APIに渡す。プロンプトに記載する必要が無い
参照: https://ai.google.dev/gemini-api/docs/image-generation?hl=ja#gemini-3-capabilities
'''
def _augment_prompt(prompt: str, aspect_ratio: Optional[str], resolution: Optional[str]) -> str:
    """README要件のパラメータをプロンプトに織り込んでAPIへ伝える。"""

    constraints: list[str] = []
    if aspect_ratio:
        constraints.append(f"Respect the requested aspect ratio: {aspect_ratio}.")
    if resolution:
        constraints.append(f"Render the final image at approximately {resolution} resolution.")
    if not constraints:
        return prompt
    extra = " ".join(constraints)
    return f"{prompt.strip()}\n\nAdditional constraints: {extra}"

'''
この関数いらないはず。解像度はパラメーターとして直接APIに渡す。
参照 https://ai.google.dev/gemini-api/docs/image-generation?hl=ja#gemini-3-capabilities
'''
def _resolution_to_media_config(resolution: Optional[str]) -> Optional[types.MediaResolution]:
    """
    READMEで例示された解像度をGoogle GeminiのMediaResolutionにマッピングする。
    - 720p: 低解像度
    - 1080p: 中解像度
    - 2K: 高解像度
    それ以外や未指定はNoneを返す。
    """

    if not resolution:
        return None

    normalized = resolution.strip().lower()
    if normalized in {"720p", "720"}:
        return types.MediaResolution.MEDIA_RESOLUTION_LOW
    if normalized in {"1080p", "1080"}:
        return types.MediaResolution.MEDIA_RESOLUTION_MEDIUM
    if normalized in {"2k", "1440p"}:
        return types.MediaResolution.MEDIA_RESOLUTION_HIGH
    return None


def generate_image(
    prompt: str,
    image: Image.Image,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
) -> GeneratedImage:
    """
    プロンプトと画像を使って画像生成APIを呼び出す関数。

    Args:
        prompt: ユーザー指定の説明文。
        image: ラフ絵(PIL Image)。
        aspect_ratio: 任意のアスペクト比文字列。
        resolution: 任意の解像度指定文字列。
    Returns:
        GeneratedImage: 生成済みPIL Imageとバイト列を含む結果。
    Raises:
        RuntimeError: API応答に画像が含まれていない場合。
    """

    request_prompt = _augment_prompt(prompt, aspect_ratio, resolution)

    generation_kwargs: dict[str, object] = {"response_mime_type": "image/png"}
    media_resolution = _resolution_to_media_config(resolution)
    if media_resolution:
        generation_kwargs["media_resolution"] = media_resolution

    response = client.models.generate_content(
        # gemini-3-pro-image-previewに差し替えること
        model="gemini-2.5-flash-image",
        contents=[request_prompt, image],
        generation_config=types.GenerationConfig(**generation_kwargs),
    )

    image_bytes: Optional[bytes] = None
    for part in response.parts:
        if getattr(part, "text", None):
            # Geminiは追加説明を返すことがあるのでログとして出力する。
            print(part.text)
        inline_data = getattr(part, "inline_data", None)
        if inline_data:
            image_bytes = inline_data.data
            break

    if image_bytes is None:
        raise RuntimeError("APIレスポンスに画像データが含まれていません。")

    byte_stream = BytesIO(image_bytes)
    generated_image = Image.open(byte_stream)
    generated_image.load()

    generated_image.save("generated_image.png")

    return GeneratedImage(
        image=generated_image,
        raw_bytes=image_bytes,
        mime_type="image/png",
        prompt=request_prompt,
    )
