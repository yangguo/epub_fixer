#!/usr/bin/env python3
"""Custom Fix Agent - Uses LLM to generate and apply tailored fixes"""

from .base_agent import BaseAgent
import os
import re
import subprocess
import json
import tempfile
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from epub_master_fixer import (
        wrap_blockquote_text as master_wrap_blockquote_text,
        ensure_image_alt_attributes as master_ensure_image_alt_attributes,
        fix_unclosed_anchor_tags as master_fix_unclosed_anchor_tags,
        fix_unclosed_p_tags as master_fix_unclosed_p_tags,
    )
except ImportError:
    master_wrap_blockquote_text = None
    master_ensure_image_alt_attributes = None
    master_fix_unclosed_anchor_tags = None
    master_fix_unclosed_p_tags = None

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
        issue_flags, issue_files = self._detect_issue_flags(error_details)
        
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
            
            # Apply deterministic fixes for known structural issues
            error_processed = False
            if issue_flags["missing_body"]:
                self.log("info", "Applying rule-based fix for missing </body> tags...")
                if self._fix_missing_body_tags(extract_dir):
                    fixed_count += 1
                    error_processed = True

            if issue_flags["blockquote"]:
                self.log("info", "Wrapping bare blockquote text inside <p> tags...")
                if self._fix_blockquote_issues(extract_dir):
                    fixed_count += 1
                    error_processed = True

            if issue_flags["missing_alt"]:
                self.log("info", "Adding fallback alt text to <img> tags...")
                if self._fix_missing_alt_attributes(extract_dir):
                    fixed_count += 1
                    error_processed = True

            anchor_files = issue_files.get("unclosed_anchor", set())
            if anchor_files:
                self.log("info", f"Closing open <a> tags in {len(anchor_files)} file(s)...")
                if self._fix_unclosed_anchor_tags(extract_dir, anchor_files):
                    fixed_count += 1
                    error_processed = True

            p_files = issue_files.get("unclosed_p", set())
            if p_files:
                self.log("info", f"Balancing <p> tags in {len(p_files)} file(s)...")
                if self._fix_unclosed_p_tags(extract_dir, p_files):
                    fixed_count += 1
                    error_processed = True

            cover_files = issue_files.get("cover_attr", set())
            if cover_files:
                self.log("info", "Cleaning invalid attributes from cover files...")
                if self._fix_cover_attributes(extract_dir, cover_files):
                    fixed_count += 1
                    error_processed = True

            toc_files = issue_files.get("missing_fragment", set())
            if toc_files:
                self.log("info", "Repairing NCX fragment identifiers...")
                if self._fix_missing_fragments(extract_dir, toc_files):
                    fixed_count += 1
                    error_processed = True

            # Process remaining errors via LLM-generated instructions
            for error in error_details:
                if issue_flags["missing_body"] and self._is_body_error(error):
                    continue
                if issue_flags["blockquote"] and self._is_blockquote_error(error):
                    continue
                if issue_flags["missing_alt"] and self._is_missing_alt_error(error):
                    continue

                if error.get("severity") == "ERROR":
                    fix_instructions = self._generate_fix_instructions(error, extract_dir)
                    if self._apply_fix(fix_instructions, extract_dir, error):
                        fixed_count += 1
                        error_processed = True
            
            # If no error details, try to find HTML files and fix body tags
            if not error_details and not error_processed:
                self.log("info", "No error details available - trying to find and fix HTML files...")
                if self._fix_missing_body_tags(extract_dir):
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
            
            content = self.llm_brain.get_response_text(response)
            if not content:
                raise ValueError("Empty fix instruction content from LLM")
            
            # Extract JSON from response
            content = self.llm_brain._extract_json(content)
            
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

    def _detect_issue_flags(self, error_details: list) -> tuple[dict, dict]:
        """Detect common issue categories that we can fix deterministically."""
        flags = {
            "missing_body": False,
            "blockquote": False,
            "missing_alt": False,
        }
        file_map = {
            "unclosed_anchor": set(),
            "unclosed_p": set(),
            "cover_attr": set(),
            "missing_fragment": set(),
        }
        for error in error_details or []:
            file_path = self._normalize_error_path(error.get("file"))
            if self._is_body_error(error):
                flags["missing_body"] = True
            if self._is_blockquote_error(error):
                flags["blockquote"] = True
            if self._is_missing_alt_error(error):
                flags["missing_alt"] = True
            if self._is_unclosed_anchor_error(error) and file_path:
                file_map["unclosed_anchor"].add(file_path)
            if self._is_unclosed_p_error(error) and file_path:
                file_map["unclosed_p"].add(file_path)
            if self._is_cover_attr_error(error) and file_path:
                file_map["cover_attr"].add(file_path)
            if self._is_missing_fragment_error(error) and file_path:
                file_map["missing_fragment"].add(file_path)
        return flags, file_map

    def _is_body_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return "body" in message and any(
            keyword in message for keyword in ("unclosed", "not closed", "missing", "terminated")
        )

    def _is_blockquote_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return "blockquote" in message

    def _is_missing_alt_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return "alt attribute" in message or "alt text" in message

    def _is_unclosed_anchor_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return 'element type "a"' in message and "terminated" in message

    def _is_unclosed_p_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return 'element type "p"' in message and "terminated" in message

    def _is_cover_attr_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        file_path = (error.get("file") or "").lower()
        return "cover" in file_path and "attribute" in message and '"class"' in message

    def _is_missing_fragment_error(self, error: dict) -> bool:
        message = (error.get("message") or "").lower()
        return "fragment identifier is not defined" in message

    def _fix_missing_body_tags(self, extract_dir: str) -> bool:
        """Add </body> tags when they're missing."""
        modified = False
        for file_path in self._iter_html_files(extract_dir):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if "<body" in content and "</body>" not in content:
                content = content.replace("</html>", "</body>\n</html>")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                modified = True
        return modified

    def _fix_blockquote_issues(self, extract_dir: str) -> bool:
        """Wrap bare blockquote text in <p> tags."""
        if master_wrap_blockquote_text is None:
            self.log("warning", "wrap_blockquote_text helper not available")
            return False

        modified = False
        for file_path in self._iter_html_files(extract_dir):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated = master_wrap_blockquote_text(content)
            if updated != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _fix_missing_alt_attributes(self, extract_dir: str) -> bool:
        """Ensure <img> tags have alt text."""
        if master_ensure_image_alt_attributes is None:
            self.log("warning", "ensure_image_alt_attributes helper not available")
            return False

        modified = False
        for file_path in self._iter_html_files(extract_dir):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated = master_ensure_image_alt_attributes(content)
            if updated != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _fix_unclosed_anchor_tags(self, extract_dir: str, files: set[str]) -> bool:
        if master_fix_unclosed_anchor_tags is None or not files:
            return False
        modified = False
        for rel_path in files:
            full_path = os.path.join(extract_dir, rel_path)
            if not os.path.exists(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            updated = master_fix_unclosed_anchor_tags(content)
            if updated != content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _fix_unclosed_p_tags(self, extract_dir: str, files: set[str]) -> bool:
        if master_fix_unclosed_p_tags is None or not files:
            return False
        modified = False
        for rel_path in files:
            full_path = os.path.join(extract_dir, rel_path)
            if not os.path.exists(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            updated = master_fix_unclosed_p_tags(content)
            if updated != content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _fix_cover_attributes(self, extract_dir: str, files: set[str]) -> bool:
        modified = False
        for rel_path in files:
            full_path = os.path.join(extract_dir, rel_path)
            if not os.path.exists(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            updated = re.sub(r'(<html[^>]*?)\s+class="[^"]*"', r'\1', content, flags=re.IGNORECASE)
            if updated != content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _fix_missing_fragments(self, extract_dir: str, files: set[str]) -> bool:
        if not files:
            return False
        fragment_index = self._build_fragment_index(extract_dir)
        modified = False
        for rel_path in files:
            full_path = os.path.join(extract_dir, rel_path)
            if not os.path.exists(full_path):
                continue
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                continue
            base_dir = os.path.dirname(rel_path)

            def replace(match):
                prefix, src_value, suffix = match.groups()
                if "#" not in src_value:
                    return match.group(0)
                file_part, fragment = src_value.split("#", 1)
                target = os.path.normpath(os.path.join(base_dir, file_part)).replace("\\", "/")
                ids = fragment_index.get(target, set())
                if not fragment or fragment not in ids:
                    return f'{prefix}{file_part}{suffix}'
                return match.group(0)

            updated = re.sub(r'(<content\s+src=")([^"]*)(")', replace, content, flags=re.IGNORECASE)
            if updated != content:
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                modified = True
        return modified

    def _build_fragment_index(self, extract_dir: str) -> dict:
        index: dict[str, set[str]] = {}
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if not file.lower().endswith((".xhtml", ".html")):
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, extract_dir).replace("\\", "/")
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    continue
                index[rel_path] = set(re.findall(r'id="([^"]+)"', content))
        return index

    def _iter_html_files(self, extract_dir: str):
        """Yield all HTML/XHTML file paths within the extracted EPUB."""
        for root, _, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith((".xhtml", ".html")):
                    yield os.path.join(root, file)

    def _normalize_error_path(self, file_path: str | None) -> str:
        if not file_path:
            return ""
        cleaned = file_path
        if ".epub/" in cleaned:
            cleaned = cleaned.split(".epub/", 1)[1]
        return cleaned.replace("\\", "/")
