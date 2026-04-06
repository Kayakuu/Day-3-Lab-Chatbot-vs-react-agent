"""Loguru-based agent cycle logger.

One log line per agent invocation, with user input, final answer, token
usage, model, latency, and an estimated USD cost.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from loguru import logger

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FILE = LOG_DIR / "agent.log"

# USD per 1M tokens. Extend as needed.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o":          {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":     {"input": 0.15, "output": 0.60},
    "gpt-4.1":         {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini":    {"input": 0.40, "output": 1.60},
}

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_FILE,
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        backtrace=False,
        diagnose=False,
        level="INFO",
        serialize=True,  # JSON lines: bound `extra` fields are included
    )
    _configured = True


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price = MODEL_PRICING.get(model)
    if not price:
        # Try a loose prefix match (e.g. "gpt-4o-2024-08-06" -> "gpt-4o")
        for key, val in MODEL_PRICING.items():
            if model.startswith(key):
                price = val
                break
    if not price:
        return 0.0
    return (input_tokens / 1_000_000) * price["input"] + (
        output_tokens / 1_000_000
    ) * price["output"]


def log_agent_cycle(
    *,
    user_input: str,
    agent_output: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_s: float,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Write one structured log line for an agent cycle and return the metrics."""
    _configure()
    cost = estimate_cost_usd(model, input_tokens, output_tokens)
    payload: Dict[str, Any] = {
        "model": model,
        "latency_s": round(latency_s, 3),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost_usd": round(cost, 6),
        "user_input": user_input,
        "agent_output": agent_output,
    }
    if extra:
        payload.update(extra)
    logger.bind(**payload).info("agent_cycle")
    return payload
