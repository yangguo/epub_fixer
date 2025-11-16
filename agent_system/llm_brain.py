"""LLM Brain using Claude for intelligent decision making"""

import os
import json
import logging
import re
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

    def get_response_text(self, response: Any) -> str:
        """Safely extract textual content from Anthropic responses."""

        blocks = getattr(response, "content", None)
        if blocks is None:
            return ""

        if isinstance(blocks, str):
            return blocks.strip()

        if not isinstance(blocks, (list, tuple)):
            blocks = [blocks]

        text_blocks = []
        thinking_blocks = []

        for block in blocks:
            block_text = getattr(block, "text", None)
            if block_text is None and isinstance(block, dict):
                block_text = block.get("text")

            if block_text:
                text_blocks.append(block_text)
                continue

            thinking_text = getattr(block, "thinking", None)
            if thinking_text is None and isinstance(block, dict):
                thinking_text = block.get("thinking")

            if thinking_text:
                thinking_blocks.append(thinking_text)

        cleaned_text = "\n".join(part.strip() for part in text_blocks if part and part.strip()).strip()
        if cleaned_text:
            return cleaned_text

        cleaned_thinking = "\n".join(part.strip() for part in thinking_blocks if part and part.strip()).strip()
        if cleaned_thinking:
            return cleaned_thinking

        if blocks:
            fallback = blocks[0]
            for attr in ("text", "thinking"):
                value = getattr(fallback, attr, None)
                if value:
                    return str(value).strip()
            if isinstance(fallback, dict):
                for key in ("text", "thinking"):
                    if fallback.get(key):
                        return str(fallback[key]).strip()
            return str(fallback).strip()

        return ""
    
    def _extract_json(self, content: str) -> str:
        """Extract JSON from potentially messy LLM response"""
        content = content.strip()
        
        # Remove markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        
        # Find which comes first: [ or {
        bracket_idx = content.find('[')
        brace_idx = content.find('{')
        
        # If both exist, use whichever comes first
        if bracket_idx != -1 and brace_idx != -1:
            if bracket_idx < brace_idx:
                # Array comes first - extract it
                bracket_count = 0
                for i in range(bracket_idx, len(content)):
                    if content[i] == '[':
                        bracket_count += 1
                    elif content[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            return content[bracket_idx:i+1]
            else:
                # Object comes first - extract it
                brace_count = 0
                for i in range(brace_idx, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return content[brace_idx:i+1]
        elif brace_idx != -1:
            # Only object exists
            brace_count = 0
            for i in range(brace_idx, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return content[brace_idx:i+1]
        elif bracket_idx != -1:
            # Only array exists
            bracket_count = 0
            for i in range(bracket_idx, len(content)):
                if content[i] == '[':
                    bracket_count += 1
                elif content[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        return content[bracket_idx:i+1]
        
        # If still no match, return the content as-is and let json.loads fail
        return content
    
    def _truncate_for_llm(self, text: str, limit: int = 60000) -> str:
        """Truncate long strings to keep LLM prompts under token limits."""
        if len(text) <= limit:
            return text
        half = limit // 2
        truncated = (
            text[:half].rstrip()
            + f"\n\n... [TRUNCATED {len(text) - limit} CHARS] ...\n\n"
            + text[-half:].lstrip()
        )
        self.logger.info(
            "Truncated epubcheck output from %s to %s characters for LLM prompt",
            len(text),
            limit,
        )
        return truncated
        
    def analyze_epub_errors(self, epubcheck_output: str) -> Dict[str, Any]:
        """Analyze epubcheck output and determine fixing strategy"""
        excerpt = self._truncate_for_llm(epubcheck_output, 60000)
        
        prompt = f"""You are an expert EPUB validation analyst. Analyze this epubcheck output and provide a structured response.

EPUBCHECK OUTPUT:
{excerpt}

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
            
            content = self.get_response_text(response)
            if not content:
                raise ValueError("Empty response content from LLM")
            self.logger.debug(f"Raw LLM response: {content[:200]}...")
            
            # Clean up the response to extract JSON
            content = self._extract_json(content)
            
            # Parse the JSON
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError as je:
                self.logger.error(f"JSON parse failed even after extraction: {je}")
                self.logger.debug(f"Cleaned content: {content[:500]}...")
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
            
            content = self.get_response_text(response)
            if not content:
                raise ValueError("Empty workflow response content from LLM")
            
            # Extract JSON from response
            content = self._extract_json(content)
            
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
            
            content = self.get_response_text(response)
            if not content:
                raise ValueError("Empty fix strategy response content from LLM")
            
            # Extract JSON from response
            content = self._extract_json(content)
            
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
            
            answer = self.get_response_text(response)
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
            
            content = self.get_response_text(response)
            if not content:
                raise ValueError("Empty error extraction response content from LLM")
            
            # Extract JSON from response
            content = self._extract_json(content)
            
            errors = json.loads(content)
            if isinstance(errors, dict):
                errors = [errors]
            return errors[:max_errors]
            
        except Exception as e:
            self.logger.error(f"Error extraction failed: {e}")
            fallback = self._parse_epubcheck_errors(epubcheck_output, max_errors)
            if fallback:
                self.logger.info("Falling back to regex-based epubcheck error parser")
            return fallback

    def _parse_epubcheck_errors(self, epubcheck_output: str, max_errors: int) -> List[Dict[str, Any]]:
        """Fallback parser for epubcheck output when LLM JSON extraction fails."""
        pattern = re.compile(r'^(ERROR|FATAL|WARNING)\(([^)]+)\):\s+([^\n\r]+)$', re.MULTILINE)
        errors: List[Dict[str, Any]] = []

        for match in pattern.finditer(epubcheck_output):
            severity_token, code, remainder = match.groups()
            severity = "WARNING" if severity_token == "WARNING" else "ERROR"

            file_path = remainder
            message = ""
            if "):" in remainder:
                location_part, message = remainder.split("):", 1)
                location_part += ")"
            else:
                location_part = remainder

            line = column = None
            line_match = re.search(r'\((\d+),\s*(\d+)\)', location_part)
            if line_match:
                line = int(line_match.group(1))
                column = int(line_match.group(2))
                file_path = location_part[:line_match.start()].rstrip()

            file_path = file_path.rstrip(" :")
            message = message.strip()

            errors.append({
                "type": code,
                "severity": severity,
                "file": file_path,
                "line": line,
                "column": column,
                "message": message,
                "suggestion": self._suggest_fix_hint(code, message.lower())
            })

            if len(errors) >= max_errors:
                break

        return errors

    def _suggest_fix_hint(self, code: str, message_lower: str) -> str:
        """Provide lightweight suggestions based on common epubcheck error codes."""
        if "body" in message_lower and ("unclosed" in message_lower or "terminated" in message_lower):
            return "Ensure each <body> tag has a closing </body> before </html>."
        if "blockquote" in message_lower:
            return "Wrap blockquote text inside <p> tags and close the </blockquote> element."
        if "alt attribute" in message_lower or "alt text" in message_lower:
            return "Provide descriptive alt text for every <img> tag."
        if code == "RSC-005" and "text not allowed here" in message_lower:
            return "Place inline text inside allowed block-level containers."
        return "Review the referenced file and fix the structural HTML issue."
