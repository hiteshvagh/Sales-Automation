from __future__ import annotations
import json
from typing import Any, Optional
import anthropic

from config.settings import ANTHROPIC_API_KEY, MODEL


class BaseAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.client = anthropic.Anthropic(api_key=api_key or ANTHROPIC_API_KEY)
        self.model = MODEL
        self.system_prompt = "You are a helpful AI assistant."

    def run(self, prompt: str, system: Optional[str] = None) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or self.system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def run_json(self, prompt: str, system: Optional[str] = None) -> Any:
        text = self.run(prompt, system)
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1:
            start = text.find("[")
            end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {}

    def run_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: Optional[str] = None,
        max_iterations: int = 10,
    ) -> str:
        sys = system or self.system_prompt
        msgs = list(messages)
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=sys,
                tools=tools,
                messages=msgs,
            )
            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""
            if response.stop_reason == "tool_use":
                msgs.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._handle_tool_call(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                msgs.append({"role": "user", "content": tool_results})
            else:
                break
        return ""

    def _handle_tool_call(self, name: str, inputs: dict) -> Any:
        return {"error": f"Tool {name} not implemented in {self.__class__.__name__}"}
