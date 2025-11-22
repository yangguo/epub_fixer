"""Defaults and instructions for the OpenAI agent SDK variant."""

import os

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
DEFAULT_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
DEFAULT_MAX_TURNS = int(os.getenv("OPENAI_AGENT_MAX_TURNS", "6"))
DEFAULT_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_BASE_URL = os.getenv("OPENAI_BASE_URL") or os.getenv("OPENAI_API_BASE")
DEFAULT_ORG = os.getenv("OPENAI_ORGANIZATION") or os.getenv("OPENAI_ORG")
DEFAULT_PROJECT = os.getenv("OPENAI_PROJECT")
DEFAULT_API_MODE = os.getenv("OPENAI_API_MODE") or os.getenv("OPENAI_API") or "chat_completions"

SYSTEM_PROMPT = (
    "You are an EPUB repair tool. Validate EPUBs with validate_epub, fix with apply_rule_based_fix, "
    "then re-validate. Keep responses brief."
)
