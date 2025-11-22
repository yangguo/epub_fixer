"""Tool functions exposed to the OpenAI Agent SDK."""

from __future__ import annotations

import os
import shutil
from typing import Any, Dict, Optional


def validate_epub(epub_path: str) -> Dict[str, Any]:
    """Run epubcheck and return structured results."""
    result: Dict[str, Any] = {
        "success": False,
        "epub_path": epub_path,
        "error_count": None,
        "warning_count": None,
        "output": None,
        "errors": [],
    }

    if not epub_path:
        result["errors"].append("No epub_path was provided.")
        return result

    if not os.path.exists(epub_path):
        result["errors"].append(f"File not found: {epub_path}")
        return result

    try:
        from .epub_utils import run_epubcheck
    except Exception as exc:  # pragma: no cover - defensive
        result["errors"].append(f"Could not import run_epubcheck: {exc}")
        return result

    output = run_epubcheck(epub_path)
    if not output:
        result["errors"].append("epubcheck output was empty; Java may be missing.")
        return result

    error_count = output.count("ERROR(") + output.count("FATAL(")
    warning_count = output.count("WARNING(")

    # Truncate output to avoid token limit issues - just include summary and first few errors
    output_lines = output.split('\n')
    truncated_output = '\n'.join(output_lines[:50]) if len(output_lines) > 50 else output
    if len(output_lines) > 50:
        truncated_output += f"\n... ({len(output_lines) - 50} more lines truncated)"

    result.update(
        {
            "success": True,
            "error_count": error_count,
            "warning_count": warning_count,
            "has_errors": error_count > 0,
            "output": truncated_output,
        }
    )
    return result


def apply_rule_based_fix(epub_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """Run the deterministic fixer and return the output path."""
    result: Dict[str, Any] = {
        "success": False,
        "epub_path": epub_path,
        "output_path": output_path,
        "backup_path": None,
        "errors": [],
    }

    if not epub_path:
        result["errors"].append("No epub_path was provided.")
        return result

    if not os.path.exists(epub_path):
        result["errors"].append(f"File not found: {epub_path}")
        return result

    try:
        from .rule_fixer import fix_epub
    except Exception as exc:  # pragma: no cover - defensive
        result["errors"].append(f"Could not import rule-based fixer: {exc}")
        return result

    if not output_path:
        stem, ext = os.path.splitext(epub_path)
        suffix = "_fixed" if not stem.endswith("_fixed") else ""
        output_path = f"{stem}{suffix}{ext}"
        result["output_path"] = output_path

    try:
        if os.path.abspath(epub_path) != os.path.abspath(output_path):
            shutil.copy2(epub_path, output_path)
            work_file = output_path
        else:
            work_file = epub_path

        fix_epub(work_file)
        backup_path = work_file.replace(".epub", "_backup.epub")

        result.update(
            {
                "success": True,
                "output_path": work_file,
                "backup_path": backup_path if os.path.exists(backup_path) else None,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive
        result["errors"].append(f"Fixing failed: {exc}")

    return result


TOOL_REGISTRY = {
    "validate_epub": validate_epub,
    "apply_rule_based_fix": apply_rule_based_fix,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "validate_epub",
            "description": "Run epubcheck to count errors and warnings for the given EPUB file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "epub_path": {
                        "type": "string",
                        "description": "Path to the EPUB file to validate.",
                    }
                },
                "required": ["epub_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_rule_based_fix",
            "description": (
                "Run the deterministic EPUB fixer. Provide output_path to control the destination; "
                "otherwise a *_fixed.epub filename is used."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "epub_path": {
                        "type": "string",
                        "description": "Path to the source EPUB file.",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Optional output path for the fixed EPUB.",
                    },
                },
                "required": ["epub_path"],
            },
        },
    },
]
