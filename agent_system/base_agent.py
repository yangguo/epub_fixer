import logging
from pathlib import Path
from typing import Optional, Dict, Any

class BaseAgent:
    """Base class for all EPUB processing agents with LLM brain support"""
    
    def __init__(self, name: str, llm_brain=None):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self.input_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.result: Dict[str, Any] = {
            "success": False, 
            "errors": [], 
            "warnings": [], 
            "output": None,
            "llm_analysis": None
        }
        self.llm_brain = llm_brain  # LLMBrain instance for intelligent decisions

    def set_input(self, input_path) -> None:
        """Set input EPUB path"""
        self.input_path = Path(input_path)
        self.logger.info(f"Input set: {self.input_path}")

    def set_output(self, output_path) -> None:
        """Set output EPUB path"""
        self.output_path = Path(output_path)
        self.logger.info(f"Output set: {self.output_path}")

    def run(self) -> dict:
        """
        Execute the agent's core logic.
        Must be implemented by subclass.
        """
        raise NotImplementedError("run() must be implemented by subclass")

    def get_result(self) -> dict:
        """Return the agent's execution result"""
        return self.result

    def log(self, level: str, message: str) -> None:
        """Log a message with the agent's context"""
        getattr(self.logger, level)(message)
    
    def ask_llm(self, question: str, context: Optional[str] = None) -> str:
        """Ask the LLM brain a question (if available)"""
        if self.llm_brain:
            return self.llm_brain.ask_question(question, context)
        return "LLM brain not available"
    
    def set_llm_brain(self, llm_brain) -> None:
        """Set the LLM brain for this agent"""
        self.llm_brain = llm_brain
        self.logger.info("LLM brain connected")
