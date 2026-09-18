from dataclasses import replace

from app.ai.llm.factory import create_note_interpreter
from app.ai.llm.providers.gemini import GeminiNoteInterpreter
from app.core.config import get_settings
from app.services.adapters import UnconfiguredNoteInterpreter


def test_factory_uses_gemini_when_key_is_configured():
    settings = replace(
        get_settings(),
        llm_provider="gemini",
        llm_model="test-model",
        gemini_api_key="test-key",
    )

    interpreter = create_note_interpreter(settings)

    assert isinstance(interpreter, GeminiNoteInterpreter)


def test_factory_is_safe_when_key_is_missing():
    settings = replace(get_settings(), gemini_api_key=None)

    interpreter = create_note_interpreter(settings)

    assert isinstance(interpreter, UnconfiguredNoteInterpreter)
