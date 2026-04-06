import os
from dotenv import load_dotenv

from src.agent.agent import ReActAgent
from src.core.local_provider import LocalProvider
from src.core.openai_provider import OpenAIProvider
from src.tools.ride_tools import (
    ask_user,
    calculate_price,
    filter_drivers,
    get_distance,
    get_policy,
    get_route_details,
    get_vehicle_types,
)

load_dotenv()

DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "local").lower()
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TOOLS = [
    {"name": "get_policy", "description": "Lookup internal policy text.", "function": get_policy},
    {"name": "get_vehicle_types", "description": "Return available vehicle categories.", "function": get_vehicle_types},
    {"name": "get_distance", "description": "Calculate route distance between two locations.", "function": get_distance},
    {"name": "calculate_price", "description": "Estimate fare for a route and vehicle type.", "function": calculate_price},
    {"name": "filter_drivers", "description": "Find available drivers that match rating and vehicle constraints.", "function": filter_drivers},
    {"name": "get_route_details", "description": "Compare road details for two cities.", "function": get_route_details},
    {"name": "ask_user", "description": "Ask the user for missing booking details.", "function": ask_user},
]


def create_provider():
    if DEFAULT_PROVIDER == "local":
        return LocalProvider(model_path=LOCAL_MODEL_PATH)
    if DEFAULT_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is required for OpenAI provider.")
        return OpenAIProvider(model_name=DEFAULT_MODEL, api_key=OPENAI_API_KEY)
    raise ValueError(f"Unsupported provider: {DEFAULT_PROVIDER}")


def main():
    provider = create_provider()
    agent = ReActAgent(llm=provider, tools=TOOLS, max_steps=5)

    print("--- Ride-Hailing ReAct Agent ---")
    while True:
        user_input = input("User: ").strip()
        if not user_input or user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break

        answer = agent.run(user_input)
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
