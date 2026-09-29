from pathlib import Path


def test_frontend_does_not_call_setvalue_without_context():
    source = Path(__file__).parents[1].joinpath("web", "session.js").read_text(encoding="utf-8")
    assert "widget.setValue(value)" not in source
    assert "widget.value = value" in source
    assert "widget.callback?.(value)" in source


def test_chat_response_does_not_populate_approved_prompt_automatically():
    source = Path(__file__).parents[1].joinpath("web", "chat.js").read_text(encoding="utf-8")
    assert "setWorkflowWidget" not in source
    assert "ui.prompt.value = result.response" not in source
    assert "state.lastGeneratedResponse = result.response || """ in source
