import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from translator import (
    SUPPORTED_LANGUAGES,
    ModelUnavailableError,
    TranslationError,
    translate,
)

load_dotenv(Path(__file__).parent / ".env")

DEFAULT_MODEL = "gpt-6-astra"
MAX_CHARS = 5000

LANGUAGE_LABELS = {
    "english": "영어",
    "japanese": "일본어",
    "vietnamese": "베트남어",
}
TAB_LABELS = {
    "english": "🇺🇸 English",
    "japanese": "🇯🇵 日本語",
    "vietnamese": "🇻🇳 Tiếng Việt",
}
# 다운로드 파일 헤더는 국기 이모지 없이 언어명만 쓴다.
FILE_LABELS = {
    "english": "English",
    "japanese": "日本語",
    "vietnamese": "Tiếng Việt",
}

# PRD 12. 오류 처리 정책
MSG_NO_API_KEY = "API 키가 설정되지 않았습니다. `.env` 또는 Secrets를 확인하세요."
MSG_EMPTY_INPUT = "번역할 글을 입력해 주세요."
MSG_TOO_LONG = f"최대 {MAX_CHARS:,}자까지 입력할 수 있습니다."
MSG_NO_LANGUAGE = "번역할 언어를 하나 이상 선택해 주세요."
MSG_API_ERROR = "번역 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
MSG_MODEL_UNAVAILABLE = "모델(`{model}`)을 사용할 수 없습니다. 모델명과 계정 권한을 확인하세요."


def get_config(name: str, default: str | None = None) -> str | None:
    """st.secrets를 먼저 보고, 없으면 환경변수(.env)에서 읽는다."""
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        # secrets.toml이 없는 로컬 환경
        pass
    return os.getenv(name) or default


def build_download_text(result: dict) -> str:
    sections = [f"[{FILE_LABELS[lang]}]\n{text}" for lang, text in result.items()]
    return "\n\n".join(sections) + "\n"


st.set_page_config(page_title="다국어 번역기", page_icon="🌐", layout="centered")

api_key = get_config("OPENAI_API_KEY")
model = get_config("OPENAI_MODEL", DEFAULT_MODEL)

with st.sidebar:
    st.header("🌐 다국어 번역기")
    st.caption(f"사용 모델: `{model}`")
    st.subheader("사용 방법")
    st.markdown(
        "1. 번역할 글을 입력합니다.\n"
        "2. 번역할 언어를 선택합니다.\n"
        "3. **번역하기** 버튼을 누릅니다."
    )
    st.subheader("주의사항")
    st.markdown(
        f"- 한 번에 최대 **{MAX_CHARS:,}자**까지 번역할 수 있습니다.\n"
        "- 원문 언어는 자동으로 감지합니다.\n"
        "- 번역에는 수 초~수십 초가 걸릴 수 있습니다."
    )

st.title("🌐 다국어 번역기")
st.caption("영어 · 일본어 · 베트남어로 한 번에 번역합니다")

text = st.text_area(
    "번역할 글을 입력하세요",
    height=200,
    placeholder="여기에 번역할 글을 입력하세요. (원문 언어는 자동 감지됩니다)",
)
st.caption(f"{len(text):,} / {MAX_CHARS:,}자", text_alignment="right")

# 가로 컨테이너는 좁은 화면에서 자동으로 줄바꿈된다.
with st.container(horizontal=True, gap="large"):
    selected = [
        lang
        for lang in SUPPORTED_LANGUAGES
        if st.checkbox(LANGUAGE_LABELS[lang], value=True, key=f"lang_{lang}")
    ]

if st.button("번역하기", type="primary", width="stretch"):
    if not text.strip():
        st.warning(MSG_EMPTY_INPUT)
    elif len(text) > MAX_CHARS:
        st.warning(MSG_TOO_LONG)
    elif not selected:
        st.warning(MSG_NO_LANGUAGE)
    elif not api_key:
        st.error(MSG_NO_API_KEY)
    else:
        # 새 요청이 실패했을 때 이전 결과가 남아 있지 않도록 먼저 비운다.
        st.session_state.pop("result", None)
        with st.spinner("번역 중입니다... 잠시만 기다려 주세요."):
            try:
                st.session_state["result"] = translate(text, selected, api_key, model)
            except ModelUnavailableError:
                st.error(MSG_MODEL_UNAVAILABLE.format(model=model))
            except TranslationError:
                # 네트워크 오류(TranslationNetworkError)와 기타 API 오류는 PRD상 같은 메시지
                st.error(MSG_API_ERROR)

# 결과는 session_state에서 그려서 탭 전환·다운로드 클릭 후에도 유지한다.
result = st.session_state.get("result")
if result:
    with st.container(border=True):
        tabs = st.tabs([TAB_LABELS[lang] for lang in result])
        for tab, (lang, translated) in zip(tabs, result.items()):
            with tab:
                st.code(translated, language=None, wrap_lines=True)

    with st.container(horizontal_alignment="center"):
        st.download_button(
            "결과 다운로드 (.txt)",
            data=build_download_text(result),
            file_name="translation.txt",
            mime="text/plain",
            icon=":material/download:",
            on_click="ignore",
        )
