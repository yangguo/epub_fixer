"""OpenAI Agents SDK wrapper for EPUB workflows."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import os

try:
    from agents import (
        Agent,
        set_default_openai_api,
        set_default_openai_client,
        set_default_openai_key,
        set_tracing_disabled,
    )
    from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError
    from agents.model_settings import ModelSettings
    from agents.run import AgentRunner
    from agents.tool import function_tool
    from openai import AsyncOpenAI
except ImportError as exc:  # pragma: no cover - defensive
    Agent = None  # type: ignore
    AgentRunner = None  # type: ignore
    ModelSettings = None  # type: ignore
    function_tool = None  # type: ignore
    MaxTurnsExceeded = ModelBehaviorError = Exception  # type: ignore
    AsyncOpenAI = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from .config import (
    DEFAULT_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_ORG,
    DEFAULT_PROJECT,
    DEFAULT_API_MODE,
    SYSTEM_PROMPT,
)
from .tools import apply_rule_based_fix, validate_epub


class OpenAIEpubAgent:
    """Runs EPUB validation/fixing through the OpenAI Agents SDK tooling."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        system_prompt: str = SYSTEM_PROMPT,
        max_turns: int = DEFAULT_MAX_TURNS,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization: Optional[str] = None,
        project: Optional[str] = None,
        api_mode: Optional[str] = None,
    ) -> None:
        if _IMPORT_ERROR:
            raise ImportError(
                "openai-agents is required. Install with: pip install -r requirements.txt"
            ) from _IMPORT_ERROR

        # Re-read env here so late-set variables are honored even if the module was imported earlier.
        env_model = os.getenv("OPENAI_MODEL")
        env_base = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
        env_org = os.getenv("OPENAI_ORG") or os.getenv("OPENAI_ORGANIZATION")
        env_project = os.getenv("OPENAI_PROJECT")
        env_api_mode = os.getenv("OPENAI_API_MODE") or os.getenv("OPENAI_API")
        self.model = model or env_model or DEFAULT_MODEL
        self.api_key = api_key or DEFAULT_API_KEY or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or env_base or DEFAULT_BASE_URL
        self.organization = organization or env_org or DEFAULT_ORG
        self.project = project or env_project or DEFAULT_PROJECT
        self.api_mode = (api_mode or env_api_mode or DEFAULT_API_MODE).strip().lower()
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.logger = logging.getLogger("openai_agent_sdk")

        # The Agents SDK enables tracing to api.openai.com by default; turn it off when we are
        # targeting a non-OpenAI base URL or when explicitly disabled via env.
        tracing_env = os.getenv("OPENAI_AGENTS_DISABLE_TRACING")
        if tracing_env and tracing_env.lower() in ("1", "true", "yes"):
            set_tracing_disabled(True)
            self.logger.info("OpenAI Agents tracing disabled via OPENAI_AGENTS_DISABLE_TRACING.")
        elif self.base_url and "api.openai.com" not in self.base_url:
            set_tracing_disabled(True)
            self.logger.info("OpenAI Agents tracing disabled for non-OpenAI base URL.")

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set. Configure env or pass api_key.")

        # Register API settings for the Agents SDK.
        set_default_openai_key(self.api_key, use_for_tracing=False)  # disable tracing for non-OpenAI endpoints
        set_default_openai_api(self.api_mode)  # use chat_completions for broader compatibility

        # If any advanced client settings are provided, build a shared client to propagate them.
        if self.base_url or self.organization or self.project:
            if AsyncOpenAI is None:  # pragma: no cover - defensive
                raise ImportError("openai package missing AsyncOpenAI client.")
            client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                organization=self.organization,
                project=self.project,
            )
            set_default_openai_client(client, use_for_tracing=False)  # disable tracing for custom endpoints
            if self.base_url:
                self.logger.info("Using custom OpenAI base URL: %s", self.base_url)

        # Build tools using the function_tool helper so schemas stay in sync with signatures.
        self.tools = [
            function_tool(validate_epub),
            function_tool(apply_rule_based_fix),
        ]

        self.agent = Agent(
            name="epub-openai-agent",
            instructions=self.system_prompt,
            tools=self.tools,
            model=self.model,
            model_settings=ModelSettings(temperature=self.temperature),
        )
        self.runner = AgentRunner()

    def _build_user_prompt(
        self, epub_path: str, output_path: Optional[str], goal: Optional[str]
    ) -> str:
        parts = []
        if goal:
            parts.append(f"Goal: {goal}")
        parts.append(f"EPUB: {epub_path}")
        if output_path:
            parts.append(f"Output: {output_path}")
        parts.append("Steps: 1) validate_epub 2) apply_rule_based_fix 3) validate_epub")
        return "\n".join(parts)

    def _extract_tool_events(self, new_items: List[Any]) -> List[Dict[str, Any]]:
        """Best-effort extraction of tool calls/results from the SDK run log."""
        events: List[Dict[str, Any]] = []
        for item in new_items:
            item_type = getattr(item, "type", "")
            raw = getattr(item, "raw_item", None)
            if item_type == "tool_call_item":
                name = None
                if hasattr(raw, "name"):
                    name = raw.name
                elif isinstance(raw, dict):
                    name = raw.get("name") or raw.get("function", {}).get("name")
                events.append({"type": "tool_call", "name": name, "raw": str(raw)})
            elif item_type == "tool_call_output_item":
                output = getattr(item, "output", None)
                name = None
                if isinstance(raw, dict):
                    name = raw.get("tool_name") or raw.get("name")
                events.append({"type": "tool_result", "name": name, "output": output})
        return events

    def run(
        self,
        epub_path: str,
        output_path: Optional[str] = None,
        goal: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the Agent SDK loop. Returns a final reply plus a trace of tool events.
        """
        prompt = self._build_user_prompt(epub_path, output_path, goal)
        self.logger.info("Starting OpenAI Agents run for %s", epub_path)

        try:
            result = self.runner.run_sync(
                self.agent,
                prompt,
                max_turns=self.max_turns,
            )
        except MaxTurnsExceeded as exc:
            return {
                "success": False,
                "reply": "",
                "transcript": [],
                "model": self.model,
                "turns": self.max_turns,
                "errors": [f"Max turns exceeded: {exc}"],
            }
        except ModelBehaviorError as exc:
            return {
                "success": False,
                "reply": "",
                "transcript": [],
                "model": self.model,
                "turns": 0,
                "errors": [f"Agent failed: {exc}"],
            }
        except Exception as exc:  # pragma: no cover - defensive
            # Extract detailed error message if available
            error_msg = str(exc)
            if hasattr(exc, 'response') and hasattr(exc.response, 'json'):
                try:
                    error_details = exc.response.json()
                    self.logger.error("API Error Details: %s", error_details)
                    error_msg = f"{exc}: {error_details}"
                except Exception:
                    pass
            return {
                "success": False,
                "reply": "",
                "transcript": [],
                "model": self.model,
                "turns": 0,
                "errors": [f"Unexpected agent error: {error_msg}"],
            }

        tool_events = self._extract_tool_events(getattr(result, "new_items", []))
        final_reply = result.final_output if result.final_output is not None else ""
        turns = len(getattr(result, "raw_responses", []) or [])

        return {
            "success": True,
            "reply": final_reply,
            "transcript": tool_events,
            "model": self.model,
            "turns": turns or self.max_turns,
        }
