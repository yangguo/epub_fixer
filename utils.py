#!/usr/bin/env python3
"""Shared utilities for EPUB processing"""

import subprocess
import os
import re
from config import JAVA_PATHS, EPUBCHECK_JAR

def run_epubcheck(epub_path, cwd="."):
    """Run epubcheck with multi-platform Java path detection"""
    for java_path in JAVA_PATHS:
        try:
            result = subprocess.run(
                [java_path, "-jar", EPUBCHECK_JAR, epub_path],
                capture_output=True, text=True, cwd=cwd, timeout=60
            )
            return result.stdout + result.stderr
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        except Exception:
            continue
    
    return "Java not found - cannot run epubcheck"


def count_errors(output):
    """Count errors and warnings from epubcheck output"""
    error_count = output.count('ERROR(') + output.count('FATAL(')
    warning_count = output.count('WARNING(')
    return error_count, warning_count
