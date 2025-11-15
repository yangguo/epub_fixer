"""LLM Brain using Claude for intelligent decision making"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    Anthropic = None

class LLMBrain:
    """Claude-powered brain for intelligent EPUB processing decisions"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        # Get configuration from parameters or environment
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        # Model selection (priority: parameter > env > default)
        self.model = model or os.getenv("CLAUDE_MODEL") or "claude-3-5-sonnet-20241022"
        
        # Base URL for custom endpoints (proxy, OpenRouter, etc.)
        self.base_url = base_url or os.getenv("ANTHROPIC_BASE_URL")
        
        # Initialize Anthropic client
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            self.logger = logging.getLogger("llm_brain")
            self.logger.info(f"Using custom API base URL: {self.base_url}")
        
        self.client = Anthropic(**client_kwargs)
        self.logger = logging.getLogger("llm_brain")
        self.logger.info(f"LLM Brain initialized with model: {self.model}")
        self.conversation_history = []
        
    def analyze_epub_errors(self, epubcheck_output: str) -> Dict[str, Any]:
        """Analyze epubcheck output and determine fixing strategy"""
        
        prompt = f"""You are an expert EPUB validation analyst. Analyze this epubcheck output and provide a structured response.

EPUBCHECK OUTPUT:
{epubcheck_output}

Provide a JSON response with:
1. error_count: total number of errors
2. warning_count: total number of warnings
3. error_categories: list of error types (e.g., "unclosed_tags", "invalid_ids", "missing_attributes")
4. severity: "critical", "high", "medium", or "low"
5. recommended_actions: ordered list of fixing steps
6. fixable: boolean - can these be automatically fixed?
7. summary: brief description of main issues

Return ONLY valid JSON, no markdown formatting."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            self.logger.debug(f"Raw LLM response: {content[:200]}...")
            
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                # Remove first line (```json or ```)
                lines = lines[1:]
                # Remove last line (```)
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            # Try to parse JSON
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as je:
                # If JSON parsing fails, try to extract JSON from text
                self.logger.warning(f"JSON parse failed, attempting extraction: {je}")
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group(0))
                else:
                    raise
            
            self.logger.info(f"LLM Analysis: {analysis.get('summary', 'N/A')}")
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"LLM response was not valid JSON: {e}")
            self.logger.debug(f"Response content: {content if 'content' in locals() else 'N/A'}")
            # Return a default analysis
            return {
                "error_count": 0,
                "warning_count": 0,
                "error_categories": [],
                "severity": "unknown",
                "recommended_actions": ["Manual review needed"],
                "fixable": False,
                "summary": f"Could not parse LLM response as JSON"
            }
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            return {
                "error_count": 0,
                "warning_count": 0,
                "error_categories": [],
                "severity": "unknown",
                "recommended_actions": [],
                "fixable": False,
                "summary": f"Analysis failed: {str(e)}"
            }
    
    def decide_workflow(self, analysis: Dict[str, Any], available_agents: List[str]) -> List[str]:
        """Decide optimal agent workflow based on error analysis"""
        
        prompt = f"""You are an EPUB workflow optimizer. Based on this error analysis, decide the optimal sequence of agents.

ERROR ANALYSIS:
{json.dumps(analysis, indent=2)}

AVAILABLE AGENTS:
{json.dumps(available_agents, indent=2)}

Available agent types:
- "validation": Run epubcheck validation
- "fixing": Apply rule-based fixes (unclosed tags, invalid IDs, namespaces)
- "drm_removal": Remove DRM and deobfuscate fonts
- "ncx_fixer": Fix NCX navigation issues
- "html_fixer": Fix HTML/XHTML structure
- "metadata_fixer": Fix OPF metadata and manifest

Return a JSON array of agent names in execution order. Consider:
1. Always start with validation to assess current state
2. Apply fixes in logical order (structure before content)
3. End with validation to verify fixes
4. Don't include agents not needed for the specific errors

Return ONLY a JSON array like: ["validation", "fixing", "validation"]"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
                if content.startswith("json"):
                    content = content[4:].strip()
            
            workflow = json.loads(content)
            self.logger.info(f"LLM Workflow: {' -> '.join(workflow)}")
            return workflow
            
        except Exception as e:
            self.logger.error(f"Workflow decision failed: {e}")
            # Fallback to default workflow
            return ["validation", "fixing", "validation"]
    
    def generate_fix_strategy(self, error_type: str, context: str) -> Dict[str, Any]:
        """Generate specific fix strategy for an error type"""
        
        prompt = f"""You are an EPUB repair specialist. Generate a fix strategy for this specific error.

ERROR TYPE: {error_type}

CONTEXT:
{context}

Provide a JSON response with:
1. fix_method: the primary approach ("regex", "xml_parser", "manual_edit")
2. steps: list of specific actions to take
3. regex_patterns: if applicable, patterns to find/replace (as dict)
4. risk_level: "low", "medium", or "high"
5. validation_needed: boolean - should we validate after this fix?

Return ONLY valid JSON."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
                if content.startswith("json"):
                    content = content[4:].strip()
            
            strategy = json.loads(content)
            return strategy
            
        except Exception as e:
            self.logger.error(f"Fix strategy generation failed: {e}")
            return {
                "fix_method": "manual_edit",
                "steps": ["Manual intervention required"],
                "regex_patterns": {},
                "risk_level": "high",
                "validation_needed": True
            }
    
    def ask_question(self, question: str, context: Optional[str] = None) -> str:
        """Ask the LLM brain a general question about EPUB processing"""
        
        messages = []
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {context}\n\nQuestion: {question}"
            })
        else:
            messages.append({"role": "user", "content": question})
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.3,
                messages=messages
            )
            
            answer = response.content[0].text
            return answer
            
        except Exception as e:
            self.logger.error(f"Question failed: {e}")
            return f"Error: {str(e)}"
    
    def extract_error_details(self, epubcheck_output: str, max_errors: int = 10) -> List[Dict[str, Any]]:
        """Extract structured error details from epubcheck output"""
        
        prompt = f"""Extract the first {max_errors} errors from this epubcheck output into structured JSON.

EPUBCHECK OUTPUT:
{epubcheck_output[:5000]}  

Return a JSON array of error objects with fields:
- type: error type (e.g., "RSC-005", "HTM-014")
- severity: "ERROR" or "WARNING"
- file: filename where error occurs
- line: line number (if available)
- column: column number (if available)
- message: error message
- suggestion: your suggested fix approach

Return ONLY valid JSON array."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2500,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
                if content.startswith("json"):
                    content = content[4:].strip()
            
            errors = json.loads(content)
            return errors
            
        except Exception as e:
            self.logger.error(f"Error extraction failed: {e}")
            return []
