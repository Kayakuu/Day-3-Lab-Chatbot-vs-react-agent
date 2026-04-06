import re
import textwrap
from typing import Any, Dict, List, Tuple, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    ReAct-style Agent that follows the Thought-Action-Observation loop.
    """

    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])

        return textwrap.dedent(f"""
        You are a helpful AI Assistant for a ride-hailing service.
        You help users with booking, policy lookup, route comparison, and vehicle selection.

        Follow the ReAct format exactly to solve multi-step requests.

        ### TOOLS:
        {tool_descriptions}

        ### FORMAT:
        Thought: your line of reasoning.
        Action: tool_name(arguments)
        Observation: result of the tool call.
        ... (repeat Thought / Action / Observation as needed)
        Final Answer: your final response.

        ### RULES:
        1. Always start with a Thought.
        2. Only call an Action when you need an external tool.
        3. If the user request can be answered directly, provide a Final Answer.
        4. Do not invent tool results; use the Observation returned by the tool.

        ### EXAMPLES:

        Case 1: Policy Inquiry (Chatbot sufficient)
        User: "What is the cancellation policy?"
        Thought: This question is policy-related and can be answered from system knowledge or tools.
        Action: get_policy("cancellation")
        Observation: Cancellation before 24h gets 100% refund.
        Final Answer: Our cancellation policy is: cancel before 24 hours for a full refund.

        Case 2: Vehicle Types Inquiry
        User: "What types of vehicles do you have?"
        Thought: Need to provide the available vehicle categories.
        Action: get_vehicle_types()
        Observation: Sedan (4 seats), SUV (7 seats), Limousine (9 seats).
        Final Answer: We offer Sedan (4 seats, economical), SUV (7 seats, spacious), and Limousine (9 seats, luxury).

        Case 3: Optimal Booking with Rating (Agent superior)
        User: "Hanoi to Sapa, 6 people, Saturday morning, driver >4.8 stars"
        Thought: Need distance, price, and a high-rating driver.
        Action: get_distance("Hanoi", "Sapa")
        Observation: 320km.
        Action: calculate_price(320, "7-seater")
        Observation: 3,500,000 VND.
        Action: filter_drivers(min_rating=4.8, vehicle_type="7-seater")
        Observation: Driver Hung Alpha (4.9 stars).
        Final Answer: I recommend a 7-seater SUV for 3,500,000 VND with driver Hung Alpha (4.9*).

        Case 4: Route Comparison (Agent superior)
        User: "Compare tunnel vs mountain pass Hai Van, which is better for photos?"
        Thought: Need route details and price comparison.
        Action: get_route_details("Da Nang", "Hue")
        Observation: Tunnel is short and toll-based, pass is scenic and free.
        Action: calculate_price(100, "tunnel")
        Observation: 1,200,000 VND.
        Action: calculate_price(150, "pass")
        Observation: 1,100,000 VND.
        Final Answer: Tunnel is faster but more expensive. The pass is cheaper and more scenic for photos.

        Case 5: Missing Information (Edge Case)
        User: "Book me a ride to the province."
        Thought: The request lacks departure, destination, and passenger count.
        Action: ask_user("Please provide departure, destination, and number of passengers.")
        Observation: Need user input.
        Final Answer: I'd be happy to help! Please tell me your departure point, destination, and how many passengers are traveling.
        """)

    def run(self, user_input: str) -> str:
        prompt = user_input.strip()
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        steps = 0

        while steps < self.max_steps:
            result = self.llm.generate(prompt, system_prompt=self.get_system_prompt())
            content = self._normalize_response(result)
            parsed = self._parse_agent_response(content)

            self.history.append({
                "step": steps + 1,
                "prompt": prompt,
                "response": content,
                "parsed": parsed,
            })

            if parsed["final_answer"]:
                logger.log_event("AGENT_END", {
                    "steps": steps + 1,
                    "final_answer": parsed["final_answer"],
                })
                return parsed["final_answer"]

            if parsed["action_name"]:
                observation = self._execute_tool(parsed["action_name"], parsed["action_args"])
                prompt += f"\nObservation: {observation}"
                steps += 1
                continue

            logger.log_event("AGENT_ABORT", {
                "steps": steps + 1,
                "content": content,
                "reason": "Unable to resolve a valid Action or Final Answer.",
            })
            return content.strip() or "I could not complete your request."

        logger.log_event("AGENT_END", {"steps": steps, "final_answer": None})
        return "Max steps reached without final answer."

    def _normalize_response(self, result: Any) -> str:
        if isinstance(result, dict):
            return str(result.get("content", "")).strip()
        return str(result).strip()

    def _parse_agent_response(self, content: str) -> Dict[str, Optional[str]]:
        thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", content, re.DOTALL)
        action_match = re.search(r"Action:\s*([a-zA-Z_]\w*)(?:\s*\((.*?)\))?", content)
        final_match = re.search(r"Final Answer:\s*(.*)", content, re.DOTALL)

        return {
            "thought": thought_match.group(1).strip() if thought_match else None,
            "action_name": action_match.group(1).strip() if action_match else None,
            "action_args": action_match.group(2).strip() if action_match and action_match.group(2) else "",
            "final_answer": final_match.group(1).strip() if final_match else None,
        }

    def _cast_value(self, value: str) -> Any:
        value = value.strip()
        if not value:
            return value

        if (value.startswith("\"") and value.endswith("\"")) or (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        lower = value.lower()
        if lower in {"true", "false"}:
            return lower == "true"

        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def _parse_tool_args(self, args: str) -> Tuple[List[Any], Dict[str, Any]]:
        positional: List[Any] = []
        keyword: Dict[str, Any] = {}

        if not args:
            return positional, keyword

        tokens = [token.strip() for token in re.split(r",\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", args) if token.strip()]
        for token in tokens:
            if "=" in token:
                key, raw_value = token.split("=", 1)
                keyword[key.strip()] = self._cast_value(raw_value)
            else:
                positional.append(self._cast_value(token))

        return positional, keyword

    def _execute_tool(self, tool_name: str, args: str) -> str:
        for tool in self.tools:
            if tool["name"] == tool_name:
                function = tool.get("function") or tool.get("callable")
                if not callable(function):
                    return f"Tool {tool_name} has no executable function."

                positional, keyword = self._parse_tool_args(args)
                try:
                    result = function(*positional, **keyword)
                    return str(result)
                except Exception as exc:
                    logger.log_event("TOOL_ERROR", {"tool": tool_name, "error": str(exc)})
                    return f"Error executing {tool_name}: {exc}"

        return f"Tool {tool_name} not found."
