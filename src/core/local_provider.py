import time
import os
from typing import Dict, Any, Optional, Generator
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from src.core.llm_provider import LLMProvider

class LocalProvider(LLMProvider):
    """
    LLM Provider for local models using LangChain and Ollama.
    """
    def __init__(self, model_name: str = "qwen2.5", base_url: str = "http://localhost:11434", temperature: float = 0):
        super().__init__(model_name=model_name)
        
        self.llm = ChatOllama(
            model=model_name,
            base_url=base_url,
            temperature=temperature
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = self.llm.invoke(messages)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        usage = {
            "prompt_tokens": response.response_metadata.get("prompt_eval_count", 0),
            "completion_tokens": response.response_metadata.get("eval_count", 0),
            "total_tokens": response.response_metadata.get("prompt_eval_count", 0) + response.response_metadata.get("eval_count", 0)
        }

        return {
            "content": response.content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": f"ollama-{self.model_name}"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        stream = self.llm.stream(messages)

        for chunk in stream:
            if chunk.content:
                yield chunk.content
