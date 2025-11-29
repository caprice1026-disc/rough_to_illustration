from __future__ import annotations

import textwrap

import streamlit as st
from PIL import Image

from illust import generate_image

st.set_page_config(page_title="ラフ絵 to イラスト", page_icon=":art:")
st.title("ラフ絵から完成イラストを生成")
st.write(
    "ラフ絵とカラー指定、任意のアスペクト比・解像度を入力して Nano Banana(Gemini API) に送信します。"
    " 完成イラストは画面でプレビューでき、そのままダウンロードできます。"
)

ASPECT_RATIO_OPTIONS = ["自動", "1:1", "4:5", "16:9"]
RESOLUTION_OPTIONS = ["自動", "1K", "2K", "4K"]


def build_prompt(color_instruction: str) -> str:
    """色指定を含めた基本プロンプトを生成する。"""

    base_prompt = textwrap.dedent(
        """
        Using the provided image of my rough drawing, create a detailed and polished illustration
        in the style of a high-quality anime. Pay close attention to the fidelity of the original sketch,
        fill in missing lines cleanly, and follow these color instructions to finish the artwork:
        {colors}
        """
    ).strip()
    return base_prompt.format(colors=color_instruction.strip() or "No specific colors were provided.")


with st.form(key="illustration_form", clear_on_submit=False):
    uploaded_file = st.file_uploader("ラフ絵（PNG/JPG/JPEG）", type=["png", "jpg", "jpeg"])
    color_instruction = st.text_area(
        "着色イメージや雰囲気",
        "帽子は赤、服は白ベースで差し色に青、肌は柔らかい色味でお願いします。",
    )
    aspect_ratio_label = st.selectbox("アスペクト比（任意）", options=ASPECT_RATIO_OPTIONS, index=0)
    resolution_label = st.selectbox("解像度（任意）", options=RESOLUTION_OPTIONS, index=0)

    if uploaded_file:
        st.image(Image.open(uploaded_file), caption="アップロードしたラフ絵", use_column_width=True)

    submitted = st.form_submit_button("イラスト生成")

if submitted:
    if not uploaded_file:
        st.error("ラフ絵ファイルをアップロードしてください。")
    else:
        aspect_ratio = None if aspect_ratio_label == "自動" else aspect_ratio_label
        resolution = None if resolution_label == "自動" else resolution_label
        prompt = build_prompt(color_instruction)

        try:
            uploaded_file.seek(0)
            rough_image = Image.open(uploaded_file).convert("RGB")
        except Exception as exc:
            st.error(f"画像の読み込みに失敗しました: {exc}")
            st.stop()

        with st.spinner("Nano Banana に送信してイラストを生成中..."):
            try:
                generated = generate_image(
                    prompt=prompt,
                    image=rough_image,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                )
            except Exception as exc:
                st.error(f"画像生成に失敗しました: {exc}")
            else:
                st.success("イラストの生成が完了しました。")
                st.image(generated.image, caption="生成されたイラスト", use_column_width=True)
                st.download_button(
                    label="生成画像をダウンロード (PNG)",
                    data=generated.raw_bytes,
                    file_name="generated_image.png",
                    mime=generated.mime_type,
                )
                with st.expander("API に渡したプロンプトを確認"):
                    st.write(generated.prompt)
