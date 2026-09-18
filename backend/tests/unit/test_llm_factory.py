from dataclasses import replace

from app.core.config import get_settings
from app.services.adapters import UnconfiguredNoteInterpreter
from app.services.interpreter.factory import create_note_interpreter
from app.services.interpreter.gemini import GeminiNoteInterpreter


def test_factory_uses_gemini_when_key_is_configured():
    settings = replace(
        get_settings(),
        llm_provider="gemini",
        llm_model="test-model",
        gemini_api_key="test-key",
    )

    assert isinstance(create_note_interpreter(settings), GeminiNoteInterpreter)


def test_factory_is_safe_when_key_is_missing():
    settings = replace(get_settings(), gemini_api_key=None)

    assert isinstance(
        create_note_interpreter(settings), UnconfiguredNoteInterpreter
    )
