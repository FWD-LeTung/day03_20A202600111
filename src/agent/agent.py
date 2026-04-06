import os
import re
import json
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

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
        You are an intelligent assistant. You have access to the following tools:
        {tool_descriptions}

        Use the following format:
        Thought: your line of reasoning.
        Action: tool_name(<JSON arguments or a plain string>)
        Observation: result of the tool call.
        ... (repeat Thought/Action/Observation if needed)
        Final Answer: your final response.

        Rules:
        - If calling a tool, prefer JSON arguments (no markdown, no backticks).
        - Use only tools listed above.
        - After you have enough info, respond with "Final Answer:" and stop.
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        system_prompt = self.get_system_prompt()
        current_prompt = user_input.strip()
        steps = 0

        while steps < self.max_steps:
            result = self.llm.generate(current_prompt, system_prompt=system_prompt)
            content = (result.get("content") or "").strip()

            # Telemetry
            try:
                tracker.track_request(
                    provider=str(result.get("provider", "unknown")),
                    model=self.llm.model_name,
                    usage=result.get("usage") or {},
                    latency_ms=int(result.get("latency_ms") or 0),
                )
            except Exception:
                pass

            logger.log_event(
                "AGENT_STEP",
                {
                    "step": steps + 1,
                    "prompt": current_prompt,
                    "llm_output": content,
                },
            )

            final = self._extract_final_answer(content)
            if final is not None:
                logger.log_event("AGENT_FINAL", {"step": steps + 1, "final": final})
                logger.log_event("AGENT_END", {"steps": steps + 1})
                return final

            action = self._extract_action(content)
            if action is None:
                # If model doesn't follow the protocol, return what it said (better than looping).
                logger.log_event("AGENT_END", {"steps": steps + 1, "reason": "no_action_no_final"})
                return content or "No response."

            tool_name, raw_args = action
            observation = self._execute_tool(tool_name, raw_args)
            logger.log_event(
                "TOOL_OBSERVATION",
                {"step": steps + 1, "tool": tool_name, "args": raw_args, "observation": observation},
            )

            current_prompt = (
                f"{current_prompt}\n\n{content}\nObservation: {observation}\n"
            )
            
            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps, "reason": "max_steps_exceeded"})
        return "Final Answer: I couldn't finish within the step limit. Please refine the query or increase max_steps."

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                fn = tool.get("func")
                if not callable(fn):
                    return f"Tool {tool_name} is not callable."

                try:
                    parsed = self._parse_tool_args(args)
                    if isinstance(parsed, dict):
                        return str(fn(**parsed))
                    if isinstance(parsed, list):
                        return str(fn(*parsed))
                    # scalar (string/number/bool/None)
                    return str(fn(parsed))
                except TypeError as e:
                    return f"Tool call argument mismatch: {e}"
                except Exception as e:
                    return f"Tool execution failed: {type(e).__name__}: {e}"
        return f"Tool {tool_name} not found."

    def _extract_action(self, text: str) -> Optional[tuple[str, str]]:
        """
        Extract the last Action line: Action: tool_name(...)
        Returns (tool_name, raw_args_inside_parentheses_or_raw)
        """
        # Prefer explicit "Action:" protocol lines.
        matches = re.findall(r"Action\s*:\s*([a-zA-Z0-9_]+)\((.*)\)\s*$", text, flags=re.MULTILINE)
        if matches:
            tool_name, raw = matches[-1]
            return tool_name.strip(), raw.strip()

        # Fallback: a single-line tool call without "Action:"
        m = re.search(r"^\s*([a-zA-Z0-9_]+)\((.*)\)\s*$", text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip(), m.group(2).strip()

        return None

    def _extract_final_answer(self, text: str) -> Optional[str]:
        m = re.search(r"Final Answer\s*:\s*(.*)\s*$", text, flags=re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        return m.group(1).strip()

    def _parse_tool_args(self, raw: str) -> Any:
        """
        Parse tool args. Supports:
        - JSON object: {"a":1}
        - JSON array: [1,2]
        - JSON string/number/bool/null: "x", 1, true
        - Otherwise: treat as a plain string (stripped of wrapping quotes if present)
        """
        s = (raw or "").strip()
        if not s:
            return {}

        # Try JSON first
        try:
            return json.loads(s)
        except Exception:
            pass

        # Strip wrapping quotes for simple cases
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s
