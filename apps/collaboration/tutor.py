from django.conf import settings

from apps.ai_tutor.services import AIServiceError, generate_text
from apps.ai_tutor.utils import AIUsageLimitError, reserve_ai_request


def ask_tutor(user, question, context=""):
    prompt = f"Learning context:\n{context}\n\nRequest:\n{question}".strip()
    if len(prompt) > settings.DATAFORGE_AI_MAX_INPUT_CHARS:
        return None, "This request exceeds the AI input limit. Please shorten the notes."
    try:
        reserve_ai_request(user)
        answer = generate_text(
            prompt,
            "You are DataForge, a careful Data Engineering tutor. Preserve supplied "
            "technical details, state uncertainty, and do not invent facts.",
            feature="shared_notebook_compilation",
        )
        return answer, None
    except (AIUsageLimitError, AIServiceError) as error:
        return None, str(error)
