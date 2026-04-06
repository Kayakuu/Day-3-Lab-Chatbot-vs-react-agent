import pytest
from src.agent.agent import ReActAgent
from src.core.llm_provider import LLMProvider
from src.tools.ride_tools import calculate_price


class StubProvider(LLMProvider):
    def __init__(self, responses):
        super().__init__(model_name="stub")
        self._responses = responses
        self._index = 0

    def generate(self, prompt: str, system_prompt: str = None):
        if self._index >= len(self._responses):
            return {"content": "Final Answer: Could not proceed."}

        response = self._responses[self._index]
        self._index += 1
        return {"content": response, "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "latency_ms": 0, "provider": "stub"}

    def stream(self, prompt: str, system_prompt: str = None):
        yield ""


def test_react_agent_runs_tool_and_returns_final_answer():
    responses = [
        'Thought: Need to calculate price.\nAction: calculate_price(320, "7-seater")',
        'Thought: Got price.\nFinal Answer: The fare is 4,480,000 VND.',
    ]
    provider = StubProvider(responses)
    tools = [
        {"name": "calculate_price", "description": "Calculate fare for a route.", "function": calculate_price}
    ]

    agent = ReActAgent(llm=provider, tools=tools, max_steps=3)
    answer = agent.run("What is the price for 320 km with a 7-seater?")

    assert answer == "The fare is 4,480,000 VND."


def test_react_agent_returns_direct_answer_when_no_action():
    responses = [
        'Thought: This is a policy question.\nFinal Answer: Cancel before 24 hours for full refund.'
    ]
    provider = StubProvider(responses)
    tools = []

    agent = ReActAgent(llm=provider, tools=tools)
    answer = agent.run("What is the cancellation policy?")

    assert answer == "Cancel before 24 hours for full refund."


if __name__ == "__main__":
    pytest.main(["-q", "tests/test_agent.py"])
