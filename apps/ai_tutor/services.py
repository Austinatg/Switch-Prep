import logging
import re

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

_SAFE_FEATURES = {
    "tutor",
    "code_assistant",
    "personalized_learning",
    "interview_simulator.question_generation",
    "interview_simulator.answer_evaluation",
    "shared_notebook_compilation",
    "community_notes_compilation",
}


def _error_diagnostics(exc, feature):
    response = getattr(exc, "response", None)
    http_status = getattr(response, "status_code", None)
    if not isinstance(http_status, int):
        candidate_status = getattr(exc, "code", None)
        http_status = candidate_status if isinstance(candidate_status, int) else None

    gemini_error_code = getattr(exc, "status", None)
    response_json = getattr(exc, "response_json", None)
    if not isinstance(gemini_error_code, str) and isinstance(response_json, dict):
        error = response_json.get("error")
        if isinstance(error, dict):
            candidate_code = error.get("status")
            if not isinstance(candidate_code, str):
                candidate_code = error.get("code")
            if isinstance(candidate_code, (str, int)):
                candidate_code = str(candidate_code)
                if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", candidate_code):
                    gemini_error_code = candidate_code
    if isinstance(gemini_error_code, str) and not re.fullmatch(
        r"[A-Za-z0-9_-]{1,64}",
        gemini_error_code,
    ):
        gemini_error_code = None

    safe_feature = feature if feature in _SAFE_FEATURES else "unknown"
    return {
        "feature": safe_feature,
        "exception_class": type(exc).__name__,
        "http_status": http_status,
        "gemini_error_code": gemini_error_code,
    }


def _log_gemini_failure(exc, feature):
    logger.error(
        "Gemini request failed: feature=%s exception_class=%s "
        "http_status=%s gemini_error_code=%s",
        *(
            _error_diagnostics(exc, feature)[key]
            for key in (
                "feature",
                "exception_class",
                "http_status",
                "gemini_error_code",
            )
        ),
    )


class AIServiceError(Exception):
    pass


class AIConfigurationError(AIServiceError):
    pass


class AIQuotaExceededError(AIServiceError):
    pass


class AIUnavailableError(AIServiceError):
    pass


def generate_text(
    prompt,
    system_instruction,
    *,
    response_mime_type=None,
    feature="unknown",
):
    if not settings.GEMINI_API_KEY or not settings.GEMINI_MODEL:
        raise AIConfigurationError(
            "The AI assistant is not configured. Please contact the site administrator."
        )
    if not isinstance(prompt, str) or not prompt.strip():
        raise AIServiceError("Please provide a valid prompt.")
    prompt_size = len(prompt.strip()) + len(system_instruction or "")
    if prompt_size > settings.DATAFORGE_AI_MAX_INPUT_CHARS:
        raise AIServiceError(
            f"Your request must not exceed "
            f"{settings.DATAFORGE_AI_MAX_INPUT_CHARS} characters."
        )

    try:
        from google import genai
        from google.genai import errors, types
    except ImportError as exc:
        raise AIConfigurationError(
            "The Gemini SDK is unavailable. Please contact the site administrator."
        ) from exc

    try:
        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options=types.HttpOptions(
                timeout=settings.DATAFORGE_AI_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt.strip(),
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=settings.DATAFORGE_AI_MAX_OUTPUT_TOKENS,
                temperature=0.7,
                response_mime_type=response_mime_type,
            ),
        )
        try:
            answer = response.text
        except ValueError as exc:
            _log_gemini_failure(exc, feature)
            raise AIUnavailableError(
                "The AI assistant could not produce a text response. Please rephrase your request."
            ) from None
        if not answer or not answer.strip():
            raise AIUnavailableError("The AI assistant returned an empty response.")
        return answer.strip()
    except errors.APIError as exc:
        _log_gemini_failure(exc, feature)
        if exc.code == 429:
            raise AIQuotaExceededError(
                "AI usage limit reached. Please try again later."
            ) from None
        if exc.code in (401, 403):
            raise AIConfigurationError(
                "The AI service could not authenticate. Please contact the site administrator."
            ) from None
        if exc.code in (500, 502, 503, 504):
            raise AIUnavailableError(
                "The AI service is temporarily unavailable. Please try again later."
            ) from None
        raise AIServiceError(
            "The AI service could not process this request. Please try again later."
        ) from None
    except (httpx.TimeoutException, httpx.NetworkError, TimeoutError, OSError) as exc:
        _log_gemini_failure(exc, feature)
        raise AIUnavailableError(
            "The AI service could not be reached. Please try again later."
        ) from None
