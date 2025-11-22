#!/usr/bin/env python3
"""Local EPUB utilities for the OpenAI Agent SDK variant (no root imports)."""

import os
import subprocess
from typing import Tuple

# Match the root defaults but keep them local to the SDK package.
EPUBCHECK_JAR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "epubcheck.jar")
)

JAVA_PATHS = [
    "java",  # System PATH
    "/mnt/c/Program Files/Java/jdk-24/bin/java.exe",  # Windows WSL
    "C:\\Program Files\\Java\\jdk-24\\bin\\java.exe",  # Windows native
    os.path.join(os.getenv("JAVA_HOME", ""), "bin", "java.exe"),  # Respect JAVA_HOME
]


def run_epubcheck(epub_path: str, cwd: str = ".") -> str:
    """Run epubcheck with basic Java path detection and return stdout+stderr."""
    for java_path in JAVA_PATHS:
        try:
            result = subprocess.run(
                [java_path, "-jar", EPUBCHECK_JAR, epub_path],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=60,
            )
            return (result.stdout or "") + (result.stderr or "")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except Exception:
            continue

    return "Java not found - cannot run epubcheck"


def count_errors(output: str) -> Tuple[int, int]:
    """Count errors and warnings from epubcheck output."""
    error_count = output.count("ERROR(") + output.count("FATAL(")
    warning_count = output.count("WARNING(")
    return error_count, warning_count
