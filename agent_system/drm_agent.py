from .base_agent import BaseAgent
import sys
import os

sys.path.append(os.path.abspath(".."))

class DRMRemovalAgent(BaseAgent):
    """Agent for removing DRM from EPUB files"""
    
    def __init__(self):
        super().__init__("drm_removal")

    def run(self) -> dict:
        if not self.input_path:
            self.log("error", "No input path set")
            self.result["errors"].append("No input path")
            return self.result

        if not self.output_path:
            self.output_path = self.input_path.parent / (self.input_path.stem + "_nodrm.epub")

        try:
            from improved_remove_drm import remove_drm
            
            self.log("info", f"Removing DRM from: {self.input_path} -> {self.output_path}")
            
            # Assuming improved_remove_drm has a remove_drm function
            result = remove_drm(str(self.input_path), str(self.output_path))
            
            if result:
                self.result["success"] = True
                self.result["output"] = str(self.output_path)
                self.log("info", f"DRM removed successfully")
            else:
                self.result["success"] = False
                self.result["errors"].append("DRM removal failed")
                self.log("error", "DRM removal failed")

        except ImportError as e:
            self.log("error", f"DRM tool import failed: {str(e)}")
            self.result["errors"].append(f"DRM tool error: {str(e)}")
        except Exception as e:
            self.log("error", f"DRM removal exception: {str(e)}")
            self.result["errors"].append(f"DRM exception: {str(e)}")

        return self.result
