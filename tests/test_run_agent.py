import builtins
import sys
import types

import run_agent


class DummyOpenAIProvider:
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key

    def generate(self, prompt: str, system_prompt: str | None = None):
        return {
            "content": "Final Answer: ok",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "latency_ms": 1,
            "provider": "dummy",
        }


def test_build_tools_monkeypatched(monkeypatch):
    bank_mod = types.SimpleNamespace(fetch_interest_rates=lambda bank_name="all", type_rate="all": "csv")
    calc_mod = types.SimpleNamespace(calculate=lambda **kwargs: {"type": "normal", "interest": 1, "total": 2})

    def fake_loader(name, path):
        return bank_mod if name == "bank_tools" else calc_mod

    monkeypatch.setattr(run_agent, "_load_module_from_path", fake_loader)
    tools = run_agent.build_tools()
    assert {t["name"] for t in tools} == {"fetch_interest_rates", "calculate"}


def test_main_exits_when_api_key_missing(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    rc = run_agent.main()
    out = capsys.readouterr().out
    assert rc == 1
    assert "OPENAI_API_KEY" in out


def test_main_runs_one_turn_then_exits(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DEFAULT_MODEL", "gemini-1.5-flash")  # should be corrected to gpt-4o
    # Prevent .env from overriding our test env vars
    monkeypatch.setattr(run_agent, "load_dotenv", lambda override=True: None)

    # Avoid importing real bank_tools dependencies
    bank_mod = types.SimpleNamespace(fetch_interest_rates=lambda bank_name="all", type_rate="all": "csv")
    calc_mod = types.SimpleNamespace(calculate=lambda **kwargs: {"type": "normal", "interest": 1, "total": 2})
    monkeypatch.setattr(run_agent, "_load_module_from_path", lambda name, path: bank_mod if name == "bank_tools" else calc_mod)

    # Avoid network OpenAI calls
    # `OpenAIProvider` is imported lazily inside main(), but importing `src.core.openai_provider`
    # would fail if `openai` isn't installed. So we inject a stub module into sys.modules.
    stub = types.ModuleType("src.core.openai_provider")
    stub.OpenAIProvider = DummyOpenAIProvider
    sys.modules["src.core.openai_provider"] = stub

    # Provide one input then exit
    inputs = iter(["hi"])
    monkeypatch.setattr(builtins, "input", lambda _: next(inputs))

    # Make agent.run deterministic: exit after 1 turn by raising EOFError on next input
    def input_then_eof(_):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError()

    monkeypatch.setattr(builtins, "input", input_then_eof)

    rc = run_agent.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Provider: openai" in out
    assert "Assistant:" in out

