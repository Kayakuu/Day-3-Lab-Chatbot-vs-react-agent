# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: [Your Name Here]
- **Student ID**: [Your ID Here]
- **Date**: April 6, 2026

---

## I. Technical Contribution (15 Points)

In this lab, I implemented the core ReAct agent architecture and created a simple tool suite to support ride-hailing use cases.

- **Modules Implemented**:
  - `src/agent/agent.py`: Completed the ReAct loop with Thought/Action/Observation parsing, tool execution, and final answer detection.
  - `src/tools/ride_tools.py`: Built a sample tool collection for policy lookup, vehicle listing, distance calculation, pricing, driver filtering, route comparison, and user clarification.
  - `run_agent.py`: Added a CLI entrypoint to instantiate the agent with either local or OpenAI providers.
  - `tests/test_agent.py`: Added unit tests with a stub provider to verify agent behavior without requiring an actual LLM.

- **Code Highlights**:
  - Implemented robust action parsing in `ReActAgent._parse_agent_response()` using regex for `Thought`, `Action`, and `Final Answer`.
  - Added `_parse_tool_args()` to handle both positional and keyword arguments for tool calls.
  - Used `logger.log_event()` in `src/telemetry/logger.py` to capture agent lifecycle events such as `AGENT_START`, `AGENT_END`, and `AGENT_ABORT`.

- **Documentation**:
  - The agent constructs a system prompt that lists available tools and includes five scenario examples, including policy lookup, vehicle type inquiry, optimized booking, route comparison, and missing-information handling.
  - During execution, the agent requests the next LLM response, parses the response, executes a tool if `Action` is present, appends the `Observation`, and repeats until `Final Answer` is produced.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: The agent sometimes returned a tool call without a valid `Observation` or failed to terminate because the LLM output did not match the expected `Action(...)` syntax.
- **Log Source**: `logs/2026-04-06.log` (or equivalent daily log file created by `src/telemetry/logger.py`). Example event: `{"event":"AGENT_ABORT","reason":"Unable to resolve a valid Action or Final Answer."}`.
- **Diagnosis**: The failure came from a mismatch between the system prompt examples and the LLM response format. The prompt needed stronger instruction on exact ReAct syntax, and the parser needed to be more tolerant of quoted arguments.
- **Solution**:
  1. Enhanced the system prompt in `ReActAgent.get_system_prompt()` with explicit examples and strict formatting rules.
  2. Improved parsing in `_parse_agent_response()` to accept tool names containing underscores and optional argument blocks.
  3. Added a fallback path: if the agent cannot parse `Action` or `Final Answer`, it now logs `AGENT_ABORT` and returns a graceful problem statement instead of looping forever.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1. **Reasoning**: The `Thought` block makes the agent explicitly explain its reasoning before calling a tool, which helps separate planning from execution. A direct chatbot may answer immediately, but the ReAct agent can decompose a multi-step request into discrete actions and verify each step by observation.
2. **Reliability**: The agent can perform worse than a chatbot when the tool chain is unnecessary or when the LLM mis-parses the tool call. In simple policy questions, a well-tuned chatbot may answer faster and more directly, while the ReAct agent may introduce extra overhead if it insists on using tools.
3. **Observation**: Observations provide explicit feedback from tools back into the prompt. This feedback is critical for the next step because it prevents the agent from acting on assumptions and allows it to update its reasoning based on concrete results.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Use an asynchronous task queue for tool execution so the agent can manage slow IO-bound tools without blocking the reasoning loop.
- **Safety**: Add a supervising LLM or a verification layer that audits each suggested `Action` before execution and prevents dangerous or hallucinated tool calls.
- **Performance**: Integrate a vector database for tool retrieval and prompt selection, and cache repeated tool results to reduce repeated calls for the same queries.

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
