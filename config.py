#!/usr/bin/env python3
"""Configuration management for EPUB tools"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# EPUBCheck Configuration
EPUBCHECK_JAR = 'epubcheck.jar'

# Java Configuration
JAVA_PATHS = [
    'java',  # System PATH
    '/mnt/c/Program Files/Java/jdk-24/bin/java.exe',  # Windows WSL
    'C:\\Program Files\\Java\\jdk-24\\bin\\java.exe',  # Windows native
    os.path.join(os.getenv('JAVA_HOME', ''), 'bin', 'java.exe'),  # Use JAVA_HOME if available
]

# LLM Configuration
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20241022')
CLAUDE_BASE_URL = os.getenv('ANTHROPIC_BASE_URL')

# Fixer Configuration
MAX_FIX_ITERATIONS = 5
BACKUP_SUFFIX = '_backup.epub'

# Debug Configuration
DEBUG = os.getenv('DEBUG', 'false').lower() in ['true', '1', 'yes']
