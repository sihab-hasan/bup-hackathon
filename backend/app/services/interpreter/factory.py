from app.core.config import Settings
from app.services.adapters import UnconfiguredNoteInterpreter
from app.services.contracts import NoteInterpreter
from app.services.interpreter.gemini import GeminiNoteInterpreter


def create_note_interpreter(settings: Settings) -> NoteInterpreter:
    if settings.llm_provider != "gemini":
        return UnconfiguredNoteInterpreter(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )
    if not settings.api_key:
        return UnconfiguredNoteInterpreter("API_KEY is not configured")
    if not settings.llm_model:
        return UnconfiguredNoteInterpreter("LLM_MODEL is not configured")

    return GeminiNoteInterpreter(
        api_key=settings.api_key,
        model=settings.llm_model,
    )
