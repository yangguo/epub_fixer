"""EPUB Agent System with Claude LLM Brain"""

from .base_agent import BaseAgent
from .orchestrator import Orchestrator

try:
    from .llm_brain import LLMBrain
    __all__ = ['BaseAgent', 'Orchestrator', 'LLMBrain']
except ImportError:
    __all__ = ['BaseAgent', 'Orchestrator']
