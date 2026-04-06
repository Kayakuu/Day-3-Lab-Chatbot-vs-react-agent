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
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
        return f"""
        You are a helpful and efficient Bus Booking Assistant (Xe Khách Assistant).
        You have access to the following tools to help users search for routes and book tickets:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response to the user.

        Remember to check for seat availability before confirming a booking.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        # This will store the running conversation including thoughts and observations
        current_context = ""
        steps = 0

        while steps < self.max_steps:
            # TODO: Step 1 - Send current_context to LLM with the system prompt
            # result = self.llm.generate(user_input + current_context, system_prompt=self.get_system_prompt())
            
            # TODO: Step 2 - Parse Thought and Action (Regex is helpful here)
            
            # TODO: Step 3 - If Action found:
            #   - Call self._execute_tool(tool_name, args)
            #   - Update current_context with Thought, Action, and Observation
            
            # TODO: Step 4 - If 'Final Answer' found -> return it
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps})
        return "Agent loop not yet implemented. Please complete Step 1-4 in run()!"

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                # TODO: Implement dynamic function calling or simple if/else
                return f"Result of {tool_name}"
        return f"Tool {tool_name} not found."
