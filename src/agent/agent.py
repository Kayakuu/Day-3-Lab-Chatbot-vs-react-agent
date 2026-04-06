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
        You are a helpful AI Assistant for a ride-hailing service. You help users book rides, inquire about policies, and compare options using available tools.

        You MUST follow the ReAct format (Thought, Action, Observation) to solve multi-step problems.

        ### TOOLS:
        {tool_descriptions}

        ### FORMAT:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.

        ### RULES:
        1. Always start with a 'Thought'
        2. If you need information from a tool, call 'Action: tool_name(args)'.
        3. Wait for the 'Observation' before the next Thought.
        4. When you have all the information, provide 'Final Answer:...'

        ### EXAMPLES:
        
        Case 1: Policy Inquiry (Chatbot sufficient)
        User: "What is the cancellation policy?"
        Thought: This is about company policy, no real-time data needed.
        Action: get_policy("cancellation")
        Observation: Cancellation before 24h gets 100% refund.
        Final Answer: Our cancellation policy is: Cancel before 24 hours for full refund.

        Case 2: Vehicle Types Inquiry
        User: "What types of vehicles do you have?"
        Thought: Need to list available vehicle categories.
        Action: get_vehicle_types()
        Observation: Sedan (4 seats), SUV (7 seats), Limousine (9 seats).
        Final Answer: We offer: Sedan (4 seats, economical), SUV (7 seats, spacious), Limousine (9 seats, luxury).

        Case 3: Optimal Booking with Rating (Agent superior)
        User: "Hanoi to Sapa, 6 people, Saturday morning, driver >4.8 stars"
        Thought 1: Calculate distance for pricing.
        Action 1: get_distance("Hanoi", "Sapa")
        Observation 1: 320km.
        Thought 2: 6 people need 7-seater. Calculate price.
        Action 2: calculate_price(320, "7-seater")
        Observation 2: 3,500,000 VND.
        Thought 3: Find drivers with rating >4.8.
        Action 3: filter_drivers(min_rating=4.8, vehicle_type="7-seater")
        Observation 3: Driver "Hung Alpha" (4.9 stars).
        Final Answer: Recommended: 7-seater SUV, Price: 3.5M VND, Driver: Hung Alpha (4.9*).

        Case 4: Route Comparison (Agent superior)
        User: "Compare tunnel vs mountain pass Hai Van, which is better for photos?"
        Thought 1: Get route details for comparison.
        Action 1: get_route_details("Da Nang", "Hue")
        Observation 1: Tunnel (short, toll 100k, fast), Pass (long, free, scenic).
        Thought 2: Calculate prices for both.
        Action 2: calculate_price(100, "tunnel") and calculate_price(150, "pass")
        Observation 2: Tunnel: 1.2M VND, Pass: 1.1M VND.
        Thought 3: Answer photo aspect.
        Final Answer: Tunnel: Faster (1.2M), Pass: Cheaper and more scenic for photos (1.1M). Recommend pass for photos.

        Case 5: Missing Information (Edge Case)
        User: "Book me a ride to the province."
        Thought: User wants booking but missing details: from, to, passengers. Cannot proceed.
        Action: ask_user("Please provide departure, destination, and number of passengers.")
        Observation: Need user input.
        Final Answer: I'd be happy to help! Please tell me your departure point, destination, and how many passengers for the best quote.
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

        while steps < self.max_steps:
            # Generate LLM response
            result = self.llm.generate(current_prompt, system_prompt=self.get_system_prompt())
            
            # Parse Thought/Action from result
            thought_match = re.search(r'Thought:\s*(.*?)(?=Action:|Final Answer:|$)', result, re.DOTALL)
            action_match = re.search(r'Action:\s*(\w+)\((.*?)\)', result)
            final_match = re.search(r'Final Answer:\s*(.*)', result, re.DOTALL)
            
            if final_match:
                # If Final Answer found -> Break loop
                logger.log_event("AGENT_END", {"steps": steps, "final_answer": final_match.group(1).strip()})
                return final_match.group(1).strip()
            
            if action_match:
                # If Action found -> Call tool -> Append Observation
                tool_name = action_match.group(1)
                args = action_match.group(2).strip()
                observation = self._execute_tool(tool_name, args)
                current_prompt += f"\nObservation: {observation}"
            else:
                # No action, perhaps continue with thought
                pass
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps})
        return "Max steps reached without final answer."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                # Assume tool has 'function' key as callable
                if 'function' in tool:
                    try:
                        # Simple parsing: assume args is comma-separated values
                        arg_list = [arg.strip() for arg in args.split(',')] if args else []
                        return str(tool['function'](*arg_list))
                    except Exception as e:
                        return f"Error executing {tool_name}: {str(e)}"
                else:
                    return f"Tool {tool_name} has no function defined."
        return f"Tool {tool_name} not found."
