import pytest
from app.prompts import (
    build_system_prompt,
    build_tool_prompt,
    parse_json_response,
)


def test_build_system_prompt():
    prompt = build_system_prompt(
        user_name="TestUser",
        memory_context="Test context",
        session_history="user: hello",
        turn_count=1,
    )
    assert "TestUser" in prompt
    assert "Test context" in prompt


def test_build_tool_prompt():
    prompt = build_tool_prompt("open Chrome")
    assert "open Chrome" in prompt
    assert "open_app" in prompt


def test_parse_json_response_valid():
    result = parse_json_response('{"tool": "chat", "args": {}, "speak": "hello"}')
    assert result["tool"] == "chat"
    assert result["speak"] == "hello"


def test_parse_json_response_markdown():
    result = parse_json_response('```json\n{"tool": "chat", "speak": "hi"}\n```')
    assert result["tool"] == "chat"


def test_parse_json_response_fallback():
    result = parse_json_response("Just a plain response")
    assert result["tool"] == "chat"
    assert "Just a plain response" in result["speak"]


def test_parse_json_response_steps():
    result = parse_json_response('{"steps": [{"tool": "open_app", "args": {}, "speak": "Opening"}]}')
    assert "steps" in result
    assert result["steps"][0]["tool"] == "open_app"