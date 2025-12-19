import pytest

deepagents = pytest.importorskip("deepagents")


def _tool_names(agent) -> set[str]:
    names: set[str] = set()

    def _collect(maybe) -> None:
        if maybe is None:
            return
        if isinstance(maybe, dict):
            for key, tool in maybe.items():
                if isinstance(key, str):
                    names.add(key)
                _collect(tool)
            return
        if isinstance(maybe, (list, tuple, set)):
            iterable = maybe
        else:
            iterable = [maybe]
        for tool in iterable:
            if isinstance(tool, str):
                names.add(tool)
                continue
            name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
            if name:
                names.add(name)
            config = getattr(tool, "config", None)
            if isinstance(config, dict) and config.get("name"):
                names.add(config["name"])

    for attr in ("tools", "available_tools", "tool_list"):
        _collect(getattr(agent, attr, None))

    list_tools = getattr(agent, "list_tools", None)
    if callable(list_tools):
        try:
            _collect(list_tools())
        except Exception:
            pass

    return names


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-tavily-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    return deepagents.create_deep_agent(model="openai:gpt-4o-mini")


def test_agent_instantiation(agent):
    assert agent is not None
    assert hasattr(agent, "invoke")


def test_builtin_middlewares_registered(agent):
    names = {name.lower() for name in _tool_names(agent)}

    if not names:
        pytest.skip("DeepAgents create_deep_agent does not expose tool metadata in this version")

    has_todo = any("write" in name and "todo" in name for name in names)
    has_filesystem_read = any("read" in name and "file" in name for name in names)
    has_subagent = any("task" in name or "subagent" in name for name in names)

    assert has_todo, f"expected todo tool names, got {names}"
    assert has_filesystem_read, f"expected filesystem tool names, got {names}"
    assert has_subagent, f"expected subagent tool names, got {names}"
