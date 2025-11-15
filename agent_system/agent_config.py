import logging
import os
from typing import Optional

def setup_logging():
    """Configure logging for the agent system"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("agent_system.log"),
            logging.StreamHandler()
        ]
    )

# Default workflow configuration
DEFAULT_WORKFLOW = [
    "validation",
    "fixing",
    "validation"
]

# Agent mapping - now accepts llm_brain parameter
AGENT_MAPPING = {
    "validation": lambda llm=None: __import__("agent_system.validation_agent", fromlist=['ValidationAgent']).ValidationAgent(llm),
    "fixing": lambda llm=None: __import__("agent_system.fixing_agent", fromlist=['FixingAgent']).FixingAgent(llm),
    "custom_fixing": lambda llm=None: __import__("agent_system.custom_fix_agent", fromlist=['CustomFixAgent']).CustomFixAgent(llm),
    "drm_removal": lambda llm=None: __import__("agent_system.drm_agent", fromlist=['DRMRemovalAgent']).DRMRemovalAgent(llm)
}

def get_agent(agent_name: str, llm_brain=None):
    """Get an agent instance by name with optional LLM brain"""
    if agent_name not in AGENT_MAPPING:
        raise ValueError(f"Unknown agent: {agent_name}")
    return AGENT_MAPPING[agent_name](llm_brain)

def create_llm_brain(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None
):
    """Create an LLM brain instance if API key is available
    
    Args:
        api_key: Anthropic API key (or set ANTHROPIC_API_KEY env)
        model: Model name (or set CLAUDE_MODEL env, default: claude-3-5-sonnet-20241022)
        base_url: Custom API base URL (or set ANTHROPIC_BASE_URL env)
    """
    try:
        from agent_system.llm_brain import LLMBrain
        return LLMBrain(api_key=api_key, model=model, base_url=base_url)
    except ImportError as e:
        logging.warning(f"Could not import LLMBrain: {e}")
        logging.warning("Install anthropic package: pip install anthropic")
        return None
    except Exception as e:
        logging.warning(f"Could not create LLM brain: {e}")
        return None
