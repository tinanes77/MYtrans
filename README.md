# 🌐 다국어 번역기

입력한 글을 영어 · 일본어 · 베트남어로 한 번에 번역하는 Streamlit 앱입니다.
번역은 OpenAI `gpt-6-astra` 모델을 사용합니다.

## 로컬 실행

```bash
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`.env.example`을 복사해 `.env`를 만들고 API 키를 입력합니다.

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-6-astra
```

```bash
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속합니다.

## Streamlit Community Cloud 배포

1. 프로젝트를 GitHub 저장소에 올립니다. `.env`는 `.gitignore`로 제외되어 있습니다.
2. https://share.streamlit.io 에서 저장소를 연결하고 메인 파일을 `app.py`로 지정합니다.
3. App settings → **Secrets**에 아래 내용을 등록합니다. (`.streamlit/secrets.toml.example` 참고)
   ```toml
   OPENAI_API_KEY = "sk-..."
   OPENAI_MODEL = "gpt-6-astra"
   ```
4. **Deploy**를 누릅니다.

앱은 Secrets를 먼저 읽고, 없으면 `.env`(환경변수)를 읽습니다.

## Docker 실행

```bash
docker build -t translator .
docker run -p 8501:8501 --env-file .env translator
```

`.env`는 `.dockerignore`로 이미지에서 제외되며, 실행 시 `--env-file`로 주입합니다.
