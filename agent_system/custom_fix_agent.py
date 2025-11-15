#!/usr/bin/env python3
"""Custom Fix Agent - Uses LLM to generate and apply tailored fixes"""

from .base_agent import BaseAgent
import os
import re
import subprocess
import json
import tempfile

class CustomFixAgent(BaseAgent):
    """Agent that uses LLM to generate custom fixes for persistent errors"""
    
    def __init__(self, llm_brain):
        super().__init__("custom_fixing", llm_brain)
        
    def run(self) -> dict:
        """Execute custom fixing logic"""
        if not self.input_path:
            self.log("error", "No input path set")
            self.result["errors"].append("No input path")
            return self.result

        if not os.path.exists(self.input_path):
            self.log("error", f"Input file not found: {self.input_path}")
            self.result["errors"].append(f"Input file not found: {self.input_path}")
            return self.result

        # 1. Get current validation errors
        validation_output = self._run_epubcheck()
        
        # 2. Extract detailed error information
        error_details = self.llm_brain.extract_error_details(validation_output, max_errors=20)
        
        if not error_details:
            self.result["success"] = True
            self.result["output"] = str(self.input_path)
            return self.result
            
        self.log("info", f"Generating custom fixes for {len(error_details)} errors...")
        
        # 3. For each error, generate and apply fixes
        fixed_count = 0
        error_count_before = len(error_details)
        
        # Extract and process the EPUB
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = os.path.join(temp_dir, "epub")
            self._extract_epub(str(self.input_path), extract_dir)
            
            # Process each error
            error_processed = False
            for error in error_details:
                if error.get("severity") == "ERROR":
                    # Check if this is a missing body tag error
                    message = error.get("message", "").lower()
                    if "body" in message and ("unclosed" in message or "missing" in message or "not closed" in message):
                        # Fallback: Apply rule-based fix for missing body tags
                        self.log("info", "Applying rule-based fix for missing </body> tags...")
                        
                        # Find all HTML/XHTML files
                        for root, _, files in os.walk(extract_dir):
                            for file in files:
                                if file.endswith((".xhtml", ".html")):
                                    file_path = os.path.join(root, file)
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read()
                                    
                                    # Fix missing </body> tag
                                    if "<body" in content and "</body>" not in content:
                                        # Add </body> before </html>
                                        content = content.replace("</html>", "</body>\n</html>")
                                        
                                        with open(file_path, "w", encoding="utf-8") as f:
                                            f.write(content)
                                        
                                        fixed_count += 1
                                        error_processed = True
                        
                        break  # Already fixed all body tag errors
                    else:
                        # Generate fix instructions for other errors
                        fix_instructions = self._generate_fix_instructions(error, extract_dir)
                        
                        # Apply the fix
                        if self._apply_fix(fix_instructions, extract_dir, error):
                            fixed_count += 1
                            error_processed = True
            
            # If no error details, try to find HTML files and fix body tags
            if not error_details or not error_processed:
                self.log("info", "No error details available - trying to find and fix HTML files...")
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        if file.endswith((".xhtml", ".html")):
                            file_path = os.path.join(root, file)
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            
                            # Fix missing </body> tag
                            if "<body" in content and "</body>" not in content:
                                # Add </body> before </html>
                                content = content.replace("</html>", "</body>\n</html>")
                                
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(content)
                                
                                fixed_count += 1
            
            # Repack the EPUB with fixes
            repacked_path = str(self.input_path) + "_temp.epub"
            self._repack_epub(extract_dir, repacked_path)
            
            # Replace original with repacked (after backup)
            self._safe_replace(self.input_path, repacked_path)
        
        # 4. Verify fixes with validation
        validation_output_after = self._run_epubcheck()
        error_count_after = validation_output_after.count('ERROR(') + validation_output_after.count('FATAL(')
        
        self.result["success"] = True
        self.result["output"] = str(self.input_path)
        self.result["llm_analysis"] = {
            "errors_fixed": max(error_count_before - error_count_after, 0),
            "fixed_count": fixed_count,
            "error_count_before": error_count_before,
            "error_count_after": error_count_after
        }
        
        self.log("info", f"Applied {fixed_count} custom fixes, {error_count_after} errors remaining")
        
        return self.result
        
    def _run_epubcheck(self) -> str:
        """Run epubcheck and return output"""
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from utils import run_epubcheck
        
        return run_epubcheck(str(self.input_path)) or "epubcheck could not be run (Java not found)"
    
    def _extract_epub(self, epub_path: str, extract_dir: str) -> None:
        """Extract EPUB content"""
        import zipfile
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    
    def _repack_epub(self, extract_dir: str, epub_path: str) -> None:
        """Repack EPUB with proper mimetype handling"""
        import zipfile
        with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            mimetype_path = os.path.join(extract_dir, 'mimetype')
            if os.path.exists(mimetype_path):
                zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
            
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == 'mimetype':
                        continue
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, extract_dir)
                    zip_ref.write(file_path, arc_path)
    
    def _generate_fix_instructions(self, error: dict, extract_dir: str) -> dict:
        """Generate fix instructions for an error"""
        # Get the actual file content for context
        file_path = error.get("file")
        file_content = ""
        
        if file_path:
            full_path = os.path.join(extract_dir, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r', encoding='utf-8') as f:
                    # Read relevant content around the error line
                    lines = f.readlines()
                    error_line = error.get("line") or 0
                    
                    start_line = max(0, error_line - 10)
                    end_line = min(len(lines), error_line + 10)
                    
                    file_content = "".join(lines[start_line:end_line])
        
        prompt = f"""
You are an expert EPUB repair specialist. Generate detailed, actionable fix instructions for this error.

ERROR DETAILS:
{json.dumps(error, indent=2)}

FILE CONTENT CONTEXT (relevant lines):
{file_content}

Please provide a JSON response with:
1. file_path: The file to modify (from error details)
2. fix_type: "regex_replacement", "xml_edit", "content_modification", "none"
3. regex_patterns: List of {{'find': 'pattern', 'replace': 'replacement'}} objects (for regex fixes)
4. changes: Specific content changes to make (for non-regex fixes)
5. explanation: Why this fix works

Return ONLY valid JSON, no markdown.
"""

        try:
            response = self.llm_brain.client.messages.create(
                model=self.llm_brain.model,
                max_tokens=1500,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0].strip()
            
            return json.loads(content)
        except Exception as e:
            self.log("error", f"Fix generation failed: {e}")
            return {"fix_type": "none"}
    
    def _apply_fix(self, fix_instructions: dict, extract_dir: str, error: dict) -> bool:
        """Apply a generated fix"""
        try:
            if fix_instructions.get("fix_type") == "regex_replacement":
                file_path = fix_instructions.get("file_path")
                if file_path:
                    full_path = os.path.join(extract_dir, file_path)
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Apply all regex replacements
                        for pattern in fix_instructions.get("regex_patterns", []):
                            content = re.sub(pattern["find"], pattern["replace"], content)
                        
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return True
            
            elif fix_instructions.get("fix_type") in ["xml_edit", "content_modification"]:
                file_path = fix_instructions.get("file_path")
                if file_path:
                    full_path = os.path.join(extract_dir, file_path)
                    if os.path.exists(full_path):
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Apply content changes (simple text replacement)
                        changes = fix_instructions.get("changes", [])
                        for change in changes:
                            if "old" in change and "new" in change:
                                content = content.replace(change["old"], change["new"])
                        
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        return True
        
        except Exception as e:
            self.log("error", f"Fix application failed: {e}")
        
        return False
    
    def _safe_replace(self, original_path: str, new_path: str) -> None:
        """Safely replace original file with new one (after backup)"""
        backup_path = str(original_path) + "_backup.epub"
        
        import shutil
        if not os.path.exists(backup_path):
            shutil.copy2(original_path, backup_path)
        
        shutil.copy2(new_path, original_path)
        os.remove(new_path)
