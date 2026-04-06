import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
        You are an intelligent assistant for vehicle booking. Tools:
        {tool_descriptions}

        CRITICAL RULES:
        1. Nếu câu hỏi yêu cầu nằm ngoài phạm vi giá xe, tuyến đi, loại xe booking, BẮT BUỘC Final Answer là: "Câu hỏi không liên quan, xin phép không trả lời."
        2. BẮT BUỘC Final Answer chỉ được dùng Tiếng Việt hoặc Tiếng Anh. Không dùng ngôn ngữ khác.

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0

        # TODO: Generate LLM response
        # result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
        
        # TODO: Parse Thought/Action from result
        
        # TODO: If Action found -> Call tool -> Append Observation
        
        # TODO: If Final Answer found -> Break loop

        while steps < self.max_steps:
            response = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            result_text = response.get("content", "")
            
            from src.telemetry.metrics import tracker
            tracker.track_request(
                provider=response.get("provider", "Unknown"),
                model=self.llm.model_name,
                usage=response.get("usage", {}),
                latency_ms=response.get("latency_ms", 0)
            )
            
            # Print info to console for debugging
            print(f"\n--- Step {steps + 1} ---")
            print(result_text)

            final_match = re.search(r"Final Answer:\s*(.*)", result_text, re.IGNORECASE | re.DOTALL)
            if final_match:
                logger.log_event("AGENT_END", {"steps": steps + 1, "status": "success"})
                return final_match.group(1).strip()

            action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)\((.*?)\)", result_text)
            if action_match:
                tool_name = action_match.group(1).strip()
                tool_args = action_match.group(2).strip()
                
                observation = self._execute_tool(tool_name, tool_args)
                print(f"Observation: {observation}")
                current_prompt += f"\n{result_text}\nObservation: {observation}\n"
            else:
                current_prompt += f"\n{result_text}\nSystem: Format error. Must use 'Action: tool_name(args)' or 'Final Answer: ...'\n"

            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps"})
        return "Failed to find final answer within max steps."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    # Auto invoke the tool's func mapped in definition
                    if 'func' in tool and callable(tool['func']):
                        return str(tool['func'](args))
                    # Fallback stub for missing implementation
                    return f"Stub Result for '{tool_name}' with args {args}"
                except Exception as e:
                    return f"Error executing {tool_name}: {e}"
        return f"Tool {tool_name} not found."
