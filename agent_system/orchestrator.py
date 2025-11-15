from typing import List, Optional, Dict, Any
from .base_agent import BaseAgent
import logging

try:
    from .llm_brain import LLMBrain
    LLM_AVAILABLE = True
except ImportError:
    LLMBrain = None
    LLM_AVAILABLE = False

class Orchestrator:
    """Orchestrates agent workflows with LLM-powered intelligence"""
    
    def __init__(self, llm_brain: Optional['LLMBrain'] = None):
        self.agents: List[BaseAgent] = []
        self.workflow_log = []
        self.logger = logging.getLogger("orchestrator")
        self.llm_brain = llm_brain
        
        if self.llm_brain:
            self.logger.info("Orchestrator initialized with LLM brain")
        else:
            self.logger.info("Orchestrator initialized without LLM brain (rule-based mode)")

    def add_agent(self, agent: BaseAgent) -> None:
        """Add an agent to the workflow"""
        if self.llm_brain:
            agent.set_llm_brain(self.llm_brain)
        self.agents.append(agent)
        self.logger.info(f"Added agent: {agent.name}")

    def set_workflow(self, agents: List[BaseAgent]) -> None:
        """Set the full workflow (replace existing agents)"""
        self.agents = agents
        if self.llm_brain:
            for agent in self.agents:
                agent.set_llm_brain(self.llm_brain)
        self.logger.info(f"Set workflow with {len(agents)} agents")

    def run_workflow(self, input_path: str, output_path: Optional[str] = None, max_attempts: int = 5) -> Dict[str, Any]:
        """
        Run the complete workflow with LLM-powered intelligence:
        1. Pass input_path to the first agent
        2. Use LLM to analyze results and adjust workflow if needed
        3. Pass output of each agent as input to the next
        4. Handle errors gracefully with LLM suggestions
        5. Loop until all errors are fixed or max attempts reached
        """
        self.logger.info(f"Starting workflow for: {input_path}")
        self.workflow_log.clear()

        current_input = input_path
        final_result: Dict[str, Any] = {
            "success": False, 
            "errors": [], 
            "output": None, 
            "workflow": [],
            "llm_insights": [],
            "attempts": 0
        }

        for attempt in range(max_attempts):
            attempt_log = []
            final_result["attempts"] = attempt + 1
            self.logger.info(f"\n--- Attempt {attempt + 1}/{max_attempts} ---")
            
            # Initialize flags for inner loop break
            inner_loop_broken = False
            agent_failure = False

            for i, agent in enumerate(self.agents):
                self.logger.info(f"Executing agent {i+1}/{len(self.agents)}: {agent.name}")
                
                # Set input (output from previous agent)
                agent.set_input(current_input)

                # Set output if provided, or let agent default
                if output_path and i == len(self.agents) - 1:
                    agent.set_output(output_path)

                # Run the agent
                result = agent.run()
                attempt_log.append({
                    "agent": agent.name,
                    "result": result.copy(),
                    "attempt": attempt + 1
                })

                # Check for failure
                if not result["success"]:
                    final_result["success"] = False
                    final_result["errors"].append(f"Agent {agent.name} failed: {result['errors']}")
                    self.logger.error(f"Workflow failed at agent {agent.name}")
                    
                    # Use LLM to suggest recovery if available
                    if self.llm_brain and result.get("errors"):
                        suggestion = self.llm_brain.ask_question(
                            f"Agent {agent.name} failed with errors: {result['errors']}. What should we try next?",
                            context=f"Workflow: {[a.name for a in self.agents]}, Failed at step {i+1}"
                        )
                        final_result["llm_insights"].append({
                            "stage": f"failure_at_{agent.name}",
                            "suggestion": suggestion
                        })
                        self.logger.info(f"LLM suggestion: {suggestion}")
                    
                    # Break both loops
                    self.workflow_log.extend(attempt_log)
                    inner_loop_broken = True
                    agent_failure = True
                    break

                # Update current_input for next agent
                if "output" in result and result["output"]:
                    current_input = result["output"]
                    self.logger.info(f"Output from {agent.name}: {current_input}")
                
                # Store LLM analysis if present
                if result.get("llm_analysis"):
                    final_result["llm_insights"].append({
                        "stage": agent.name,
                        "analysis": result["llm_analysis"],
                        "attempt": attempt + 1
                    })
            
            # If we completed all agents without breaking
            else:
                self.workflow_log.extend(attempt_log)
                
                # Check if validation passed (no errors)
                last_agent_result = attempt_log[-1]["result"]
                if (attempt_log[-1]["agent"] == "validation" and 
                    last_agent_result.get("error_count", 0) == 0):
                    self.logger.info(f"✓ All errors fixed after {attempt + 1} attempts!")
                    break
                
                # Check if errors are decreasing (progress is being made)
                if attempt > 0:
                    prev_attempt = self.workflow_log[-len(self.agents)-len(self.agents):-len(self.agents)]
                    if prev_attempt:
                        prev_validation = next((res for res in reversed(prev_attempt) if res["agent"] == "validation"), None)
                        current_validation = next((res for res in reversed(attempt_log) if res["agent"] == "validation"), None)
                        
                        if prev_validation and current_validation:
                            prev_errors = prev_validation["result"].get("error_count", 0)
                            current_errors = current_validation["result"].get("error_count", 0)
                            
                            if current_errors >= prev_errors:
                                self.logger.warning(f"⚠ No progress with default workflow - errors remaining: {current_errors}")
                                
                                # Try custom fixing if LLM is available
                                if self.llm_brain:
                                    # Check if custom_fixing agent is already in the workflow
                                    has_custom_agent = any(agent.name == "custom_fixing" for agent in self.agents)
                                    
                                    if not has_custom_agent:
                                        self.logger.info("🔄 Switching to custom LLM-powered fixing...")
                                        
                                        # Add custom_fixing agent to workflow
                                        from agent_system.custom_fix_agent import CustomFixAgent
                                        custom_agent = CustomFixAgent(self.llm_brain)
                                        self.agents.insert(1, custom_agent)  # Insert after first validation
                                        
                                        # Continue to next attempt with the enhanced workflow
                                        continue  # Restart loop with updated workflow
                                        

                                        
        # After inner loop:
                                        
        # 1. If agent failed → break outer loop
                                        
        # 2. If custom agent added → continue to next attempt with enhanced workflow
                                        
        # 3. Otherwise → proceed to result processing
                                        
        # Finalize result
        # Success if no errors during execution AND final validation passed
        last_result = None
        for entry in reversed(self.workflow_log):
            if entry["agent"] == "validation":
                last_result = entry["result"]
                break
        
        if last_result:
            final_result["error_count"] = last_result.get("error_count", 0)
            final_result["warning_count"] = last_result.get("warning_count", 0)
        
        if not final_result["errors"] and last_result and last_result.get("error_count", 0) == 0:
            final_result["success"] = True
        elif not final_result["errors"] and len(self.workflow_log) > 0:
            # Still completed without agent failures
            final_result["success"] = True
        
        final_result["output"] = current_input
        final_result["workflow"] = self.workflow_log
        
        status = "successfully" if final_result["success"] and (last_result and last_result.get("error_count", 0) == 0) else "with remaining errors"
        self.logger.info(f"\nWorkflow completed {status} after {final_result['attempts']} attempts")
        return final_result

    def get_workflow_log(self) -> List[dict]:
        """Return the full workflow log"""
        return self.workflow_log
    def set_llm_brain(self, llm_brain) -> None:
        """Set or update the LLM brain"""
        self.llm_brain = llm_brain
        for agent in self.agents:
            agent.set_llm_brain(llm_brain)
        self.logger.info("LLM brain connected to orchestrator and all agents")
