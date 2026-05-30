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

BR_TAG_PATTERN = re.compile(r'(?i)<br\b([^>]*)>')


def find_unclosed_br_tags(content):
    """Return True if the content contains raw <br> tags that are not self-closed."""
    for match in BR_TAG_PATTERN.finditer(content):
        attrs = match.group(1) or ''
        if not attrs.rstrip().endswith('/'):
            return True
    return False


def fix_unclosed_br_tags(content):
    """Convert unclosed <br> tags to self-closing XHTML form."""
    def replace(match):
        attrs = match.group(1) or ''
        if attrs.rstrip().endswith('/'):
            return match.group(0)
        return f'<br{attrs.rstrip()} />'

    return BR_TAG_PATTERN.sub(replace, content)
