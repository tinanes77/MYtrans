"""OpenAI를 이용한 번역 로직. Streamlit에 의존하지 않는다."""

import json

import openai
from openai import OpenAI

SUPPORTED_LANGUAGES = ("english", "japanese", "vietnamese")

SYSTEM_PROMPT = """You are a professional translator.
Detect the language of the user's text automatically; it may be any language.
Translate it into the requested languages.
- Preserve the original meaning, tone, and formatting (line breaks, lists).
- If the text is already in a requested language, return it unchanged for that key.
- Do not add explanations.
- Return ONLY a JSON object with keys: {keys}
  (include only the requested keys; each value is the translated text as a string)."""

# JSON 파싱 실패 시 언어 하나씩 번역할 때 사용하는 프롬프트 (일반 텍스트로 응답)
SINGLE_PROMPT = """You are a professional translator.
Detect the language of the user's text automatically and translate it into {language}.
- Preserve the original meaning, tone, and formatting (line breaks, lists).
- Respond with ONLY the translated text, with no explanations or quotes."""

REQUEST_TIMEOUT = 60  # 초


class TranslationError(Exception):
    """번역 실패의 공통 부모 클래스."""


class TranslationNetworkError(TranslationError):
    """네트워크 연결 실패 또는 타임아웃."""


class ModelUnavailableError(TranslationError):
    """모델이 없거나 계정에 사용 권한이 없음."""


class TranslationAPIError(TranslationError):
    """그 밖의 API 오류 (인증, 사용량 제한, 서버 오류, 잘못된 응답 등)."""


def translate(text: str, languages: list[str], api_key: str, model: str) -> dict:
    """text를 languages로 번역해 {언어: 번역문} dict를 반환한다.

    1회 호출로 JSON을 받고, 파싱에 실패하거나 빠진 언어가 있으면
    해당 언어만 개별 호출로 다시 번역한다.
    """
    client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT)

    try:
        result = _translate_all(client, model, text, languages)
    except json.JSONDecodeError:
        result = {}

    for lang in languages:
        if not result.get(lang):
            result[lang] = _translate_one(client, model, text, lang)

    return {lang: result[lang] for lang in languages}


def _translate_all(client: OpenAI, model: str, text: str, languages: list[str]) -> dict:
    content = _complete(
        client,
        model,
        system=SYSTEM_PROMPT.format(keys=", ".join(languages)),
        user=text,
        json_mode=True,
    )
    data = json.loads(content)
    if not isinstance(data, dict):
        raise json.JSONDecodeError("응답이 JSON 객체가 아닙니다", content, 0)
    return {k: v.strip() for k, v in data.items() if k in languages and isinstance(v, str)}


def _translate_one(client: OpenAI, model: str, text: str, language: str) -> str:
    content = _complete(
        client,
        model,
        system=SINGLE_PROMPT.format(language=language.capitalize()),
        user=text,
        json_mode=False,
    )
    if not content.strip():
        raise TranslationAPIError(f"{language} 번역 결과가 비어 있습니다.")
    return content.strip()


def _complete(client: OpenAI, model: str, system: str, user: str, json_mode: bool) -> str:
    """Chat Completions를 호출하고, SDK 예외를 TranslationError 계열로 변환한다."""
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        # gpt-6-astra는 temperature 기본값(1)만 지원하므로 지정하지 않는다.
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            **kwargs,
        )
    except (openai.APIConnectionError, openai.APITimeoutError) as e:
        raise TranslationNetworkError(str(e)) from e
    except (openai.NotFoundError, openai.PermissionDeniedError) as e:
        raise ModelUnavailableError(str(e)) from e
    except openai.BadRequestError as e:
        if getattr(e, "code", None) == "model_not_found":
            raise ModelUnavailableError(str(e)) from e
        raise TranslationAPIError(str(e)) from e
    except openai.OpenAIError as e:
        raise TranslationAPIError(str(e)) from e

    return response.choices[0].message.content or ""
