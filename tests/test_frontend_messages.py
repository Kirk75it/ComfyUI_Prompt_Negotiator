from pathlib import Path


def test_frontend_supports_timestamp_selection_and_copy():
    source = Path(__file__).parents[1].joinpath("web", "dom.js").read_text(encoding="utf-8")
    assert "pn-message-time" in source
    assert "pn-selected" in source
    assert "navigator.clipboard.writeText" in source
    assert "message.metadata" in source
    assert "suggestions" in source


def test_approval_is_message_sequence_based():
    source = Path(__file__).parents[1].joinpath("web", "node.js").read_text(encoding="utf-8")
    assert "message_sequence" in source
    assert "state.selectedMessageSequence" in source
    assert "final_prompt: finalPrompt" not in source


def test_frontend_sends_response_mode():
    source = Path(__file__).parents[1].joinpath("web", "chat.js").read_text(encoding="utf-8")
    session_source = Path(__file__).parents[1].joinpath("web", "session.js").read_text(encoding="utf-8")
    assert "inputIsConnected(state.node, \"response_mode\")" in source
    assert "connected(\"response_mode\")" not in source
    assert '"response_mode"' in session_source

def test_frontend_parser_has_raw_content_fallback():
    source = Path(__file__).parents[1].joinpath("web", "dom.js").read_text(encoding="utf-8")
    assert "parseStructuredAssistantResponse" in source
    assert "message.content" in source
    assert 'mode === "parser"' in source
    assert "normalizeSuggestions" in source

