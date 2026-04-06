from typing import Any, Dict, List

from src.agent.agent import ReActAgent
from src.tools.calculate import calculate


class FakeLLM:
    def __init__(self, outputs: List[str], model_name: str = "fake-model"):
        self.model_name = model_name
        self._outputs = outputs
        self._i = 0

    def generate(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        if self._i >= len(self._outputs):
            content = "Final Answer: (no more outputs)"
        else:
            content = self._outputs[self._i]
        self._i += 1
        return {
            "content": content,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "latency_ms": 1,
            "provider": "fake",
        }


def test_agent_executes_tool_then_finishes():
    tools = [
        {
            "name": "calculate",
            "description": "calc tool",
            "func": calculate,
        }
    ]

    llm = FakeLLM(
        outputs=[
            'Thought: need compute\nAction: calculate({"amount":100000000,"rate":6.0,"duration":12})',
            "Final Answer: done",
        ]
    )
    agent = ReActAgent(llm=llm, tools=tools, max_steps=5)
    out = agent.run("compute interest")
    assert out == "done"


def test_agent_returns_raw_output_when_no_action_or_final():
    tools = [{"name": "calculate", "description": "calc tool", "func": calculate}]
    llm = FakeLLM(outputs=["Hello there"])
    agent = ReActAgent(llm=llm, tools=tools, max_steps=2)
    out = agent.run("hi")
    assert out == "Hello there"

