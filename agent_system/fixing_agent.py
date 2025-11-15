from .base_agent import BaseAgent
import sys
import os

# Add root directory to path to import the fixer
sys.path.append(os.path.abspath(".."))

class FixingAgent(BaseAgent):
    """Agent for fixing EPUB files using the master fixer with LLM guidance"""
    
    def __init__(self, llm_brain=None):
        super().__init__("fixing", llm_brain)

    def run(self) -> dict:
        if not self.input_path:
            self.log("error", "No input path set")
            self.result["errors"].append("No input path")
            return self.result

        if not self.output_path:
            # Default to input_path_fixed.epub - avoid multiple "_fixed" suffixes
            stem = self.input_path.stem
            if stem.endswith("_fixed"):
                # Already has fixed suffix, use as is
                self.output_path = self.input_path.parent / (stem + ".epub")
            else:
                self.output_path = self.input_path.parent / (stem + "_fixed.epub")
            self.log("info", f"Output path not set, using default: {self.output_path}")

        try:
            # Import the fixer
            try:
                from epub_master_fixer import fix_epub
            except ImportError:
                # Try alternative import path
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "epub_master_fixer",
                    os.path.join(os.path.dirname(__file__), "..", "epub_master_fixer.py")
                )
                if spec and spec.loader:
                    epub_master_fixer = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(epub_master_fixer)
                    fix_epub = epub_master_fixer.fix_epub
                else:
                    raise ImportError("Could not import epub_master_fixer")
            
            self.log("info", f"Fixing EPUB: {self.input_path} -> {self.output_path}")
            
            # If LLM brain is available, get fixing strategy
            if self.llm_brain:
                # Run a quick validation first to get errors
                import subprocess
                try:
                    import sys
                    import os
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
                    from utils import run_epubcheck
                    validation_output = run_epubcheck(str(self.input_path))                    
                    # Get LLM analysis
                    self.log("info", "Getting LLM fixing strategy...")
                    analysis = self.llm_brain.analyze_epub_errors(validation_output)
                    self.result["llm_analysis"] = analysis
                    
                    self.log("info", f"LLM recommends: {', '.join(analysis.get('recommended_actions', []))}")
                    
                    # Store recommendations for the fixer
                    self.result["recommended_actions"] = analysis.get("recommended_actions", [])
                    
                except Exception as e:
                    self.log("warning", f"Could not get LLM strategy: {e}")
            
            # fix_epub modifies the file in place and creates a backup
            # We need to copy the input to output location first
            import shutil
            
            # Copy input to output path if different
            if str(self.input_path) != str(self.output_path):
                shutil.copy2(self.input_path, self.output_path)
                work_file = self.output_path
            else:
                work_file = self.input_path
            
            # Run the fixer on the work file
            fix_epub(str(work_file))
            
            # Check if fixing succeeded (file exists and backup was created)
            backup_path = str(work_file).replace('.epub', '_backup.epub')
            if os.path.exists(work_file):
                self.result["success"] = True
                self.result["output"] = str(work_file)
                self.log("info", f"✓ EPUB fixed successfully: {work_file}")
                if os.path.exists(backup_path):
                    self.log("info", f"  Backup saved: {backup_path}")
            else:
                self.result["success"] = False
                self.result["errors"].append("Fixing process failed - no output file created")
                self.log("error", "EPUB fixing failed")

        except ImportError as e:
            self.log("error", f"Could not import fixer: {str(e)}")
            self.result["errors"].append(f"Fixer import error: {str(e)}")
        except Exception as e:
            self.log("error", f"Fixing failed: {str(e)}")
            self.result["errors"].append(f"Fixing exception: {str(e)}")
            import traceback
            self.log("debug", traceback.format_exc())

        return self.result
