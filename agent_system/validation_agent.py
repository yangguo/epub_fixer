from .base_agent import BaseAgent
import subprocess
import os

class ValidationAgent(BaseAgent):
    """Agent for validating EPUB files using epubcheck with LLM analysis"""
    
    def __init__(self, llm_brain=None):
        super().__init__("validation", llm_brain)

    def run(self) -> dict:
        if not self.input_path:
            self.log("error", "No input path set")
            self.result["errors"].append("No input path")
            return self.result

        if not os.path.exists(self.input_path):
            self.log("error", f"Input file not found: {self.input_path}")
            self.result["errors"].append(f"Input file not found: {self.input_path}")
            return self.result

        if not os.path.exists("epubcheck.jar"):
            self.log("error", "epubcheck.jar not found")
            self.result["errors"].append("epubcheck.jar not found")
            return self.result

        self.log("info", f"Validating EPUB: {self.input_path}")
        try:
            # Use shared utility to run epubcheck
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from utils import run_epubcheck
            output = run_epubcheck(str(self.input_path))
            
            if not output:
                self.log("error", "Java not found - cannot run epubcheck")
                self.result["errors"].append("Java not found")
                return self.result

            # Parse results
            error_count = output.count('ERROR(') + output.count('FATAL(')
            warning_count = output.count('WARNING(')
            
            # Use LLM to analyze errors if available
            if self.llm_brain and error_count > 0:
                self.log("info", "Analyzing errors with LLM brain...")
                analysis = self.llm_brain.analyze_epub_errors(output)
                self.result["llm_analysis"] = analysis
                
                # Extract detailed errors
                detailed_errors = self.llm_brain.extract_error_details(output, max_errors=10)
                self.result["detailed_errors"] = detailed_errors
                
                self.log("info", f"LLM Analysis: {analysis.get('summary', 'N/A')}")
                self.log("info", f"Severity: {analysis.get('severity', 'unknown')}")
                self.log("info", f"Fixable: {analysis.get('fixable', False)}")
            
            # ValidationAgent always succeeds (allows workflow to continue)
            # It just reports what it found
            self.result["success"] = True
            self.result["validation_output"] = output
            self.result["error_count"] = error_count
            self.result["warning_count"] = warning_count
            self.result["has_errors"] = error_count > 0
            self.result["output"] = str(self.input_path)  # Pass through for next agent
            
            if error_count == 0:
                self.log("info", f"✓ Validation passed ({warning_count} warnings)")
            else:
                self.log("warning", f"✗ Validation found {error_count} errors, {warning_count} warnings")

        except Exception as e:
            self.log("error", f"Validation failed: {str(e)}")
            self.result["errors"].append(f"Validation exception: {str(e)}")

        return self.result
