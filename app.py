import streamlit as st
import openai
import pandas as pd
import base64
from PIL import Image
from io import BytesIO
import re

# Streamlit 페이지 설정
st.set_page_config(page_title="이미지 OCR & 번역", layout="wide")

# 사이드바 설정
st.sidebar.header("설정")
api_key = st.sidebar.text_input("🔑 OpenAI API Key 입력", type="password")

uploaded_files = st.sidebar.file_uploader(
    "📂 이미지 파일 업로드 (여러 개 가능)", 
    type=["png", "jpg", "jpeg"], 
    accept_multiple_files=True
)

st.sidebar.markdown("---")

# API 키 확인
if not api_key:
    st.warning("⚠ OpenAI API Key를 입력하세요.")
    st.stop()

# OpenAI 클라이언트 초기화 (최신 API 방식)
client = openai.OpenAI(api_key=api_key)

# 이미지 Base64 인코딩 함수
def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# XML 데이터 파싱 함수
def parse_xml(xml_content):
    pattern = r'<result\d*>\s*<text\d*>(.*?)</text\d*>\s*<translation\d*>(.*?)</translation\d*>\s*</result\d*>'
    matches = re.findall(pattern, xml_content, re.DOTALL)
    return matches

# 이미지에서 OCR 및 번역 수행
def process_image(image):
    base64_image = encode_image(image)

    prompt = """
    <task>
        <instruction>
            이미지에서 영문 텍스트를 추출하고, 해당 텍스트를 한글로 번역하세요.
            하나의 이미지는 하나의 <result> 태그 안에 위치하고, 추출된 텍스트는 마침표 단위로 연결시키세요.
            반드시 하나의 이미지별 하나의 <result> 태그만 존재해야 합니다.
            결과는 다음과 같은 XML 형식으로 작성하세요:
            <result1>
                <text1>추출된 영문 텍스트</text1>
                <translation1>한글 번역</translation1>
            </result1>
        </instruction>
    </task>
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]}
            ],
            max_tokens=2000
        )

        result_xml = response.choices[0].message.content
        parsed_data = parse_xml(result_xml)

        if parsed_data:
            text, translation = parsed_data[0]  # 첫 번째 <result> 만 사용
            return text.strip(), translation.strip()
        else:
            return "추출 실패", "번역 실패"

    except Exception as e:
        return f"오류 발생: {str(e)}", "번역 불가"

# 업로드된 이미지 처리
results = []
if uploaded_files:
    for uploaded_file in uploaded_files:
        image = Image.open(uploaded_file)
        text, translation = process_image(image)

        results.append({
            "파일 이름": uploaded_file.name,
            "영문 텍스트": text,
            "한글 번역": translation
        })

    df = pd.DataFrame(results)

    # 데이터 출력
    st.write("### 🔍 OCR 결과")
    st.dataframe(df)

    # 엑셀 다운로드 기능
    def convert_df_to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="OCR 결과")
        processed_data = output.getvalue()
        return processed_data

    st.download_button(
        label="📥 엑셀 다운로드",
        data=convert_df_to_excel(df),
        file_name="ocr_translation_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
