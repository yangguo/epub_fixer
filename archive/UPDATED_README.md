# EPUB Agent System - Enhanced with Custom LLM Fixing

## Overview

The EPUB Agent System is an enhanced automated EPUB validation and repair tool that uses LLM-powered custom fixes for persistent errors.

## Core Features

### 🧠 **Enhanced LLM Integration**
- **CustomFixAgent**: Generates error-specific fixes using Claude LLM
- **Smart Stall Detection**: Automatically switches to custom fixing when default workflow fails
- **Error-Specific Fixes**: Tailors fixes to the exact errors in the EPUB

### 🔧 **Default Workflow**
```
validation → fixing → validation
```

### 🚀 **Enhanced Workflow (LLM Enabled)**
```
validation → custom_fixing → fixing → validation
```

### 📋 **Available Agents**
1. **validation**: Validates EPUB files using epubcheck
2. **fixing**: Applies rule-based fixes from `epub_master_fixer.py`
3. **custom_fixing**: LLM-powered custom fixes (new!)
4. **drm_removal**: Removes DRM protection

## Usage

### Basic Usage (with LLM):
```bash
python epub_agent_cli.py <ebook.epub> --llm --max-attempts 5
```

### Direct Custom Fixing:
```bash
python epub_agent_cli.py <ebook.epub> --llm --workflow validation custom_fixing validation
```

### With DRM Removal:
```bash
python epub_agent_cli.py <ebook.epub> --llm --drm
```

## Installation

1. **Requirements**:
   - Python 3.9+
   - Java (for epubcheck)
   - LLM API Key (Anthropic Claude recommended)

2. **Setup**:
   ```bash
   pip install -r requirements.txt
   ```

3. **API Configuration**:
   - Set `ANTHROPIC_API_KEY` in `.env` or pass via `--api-key`

## How It Works

### 1. **Stall Detection**
The Orchestrator monitors error counts between iterations. If no progress is made:
   - Detects the stall
   - Checks for LLM availability
   - Adds `CustomFixAgent` to the workflow

### 2. **Custom Fixing Process**
When `CustomFixAgent` runs:
   - Extracts detailed error information using LLM
   - Generates error-specific fix instructions
   - Applies regex and content edits to the EPUB
   - Repacks and validates the EPUB

### 3. **Safety Features**
- **Automatic Backups**: Creates `_backup.epub` files before modifications
- **Dual Java Paths**: Cross-platform support for epubcheck
- **Validation Checks**: Validates after each fixing step

## Configuration Options

| Option | Description |
|--------|-------------|
| `--llm` | Enable LLM integration |
| `--max-attempts` | Max fixing iterations (default: 5) |
| `--drm` | Enable DRM removal |
| `--workflow` | Custom workflow sequence |
| `--api-key` | LLM API key |
| `--model` | LLM model name |
| `--base-url` | Custom LLM API base URL |

## Files Modified

1. `agent_system/config.py`: Added custom_fixing agent mapping
2. `agent_system/orchestrator.py`: Enhanced with stall detection and custom agent logic
3. `agent_system/custom_fix_agent.py`: New custom fix agent implementation
4. `epub_agent_cli.py`: Updated help text

## Example Workflow

```
$ python epub_agent_cli.py my_ebook.epub --llm
🧠 Initializing Claude LLM brain...
✓ LLM brain initialized (model: claude-3-5-sonnet-20241022)
🔧 Workflow: validation -> fixing -> validation

--- Attempt 1/5 ---
📋 Results: 15 errors → 12 errors
   ✓ Fixed 3 errors!

--- Attempt 2/5 ---
⚠ No progress with default workflow - errors remaining: 12
🔄 Switching to custom LLM-powered fixing...

--- Attempt 3/5 ---
📋 Results: 12 errors → 5 errors
   ✓ Fixed 7 errors!

--- Attempt 4/5 ---
📋 Results: 5 errors → 0 errors
   🎉 All errors fixed!

Status: ✓ SUCCESS
Output: my_ebook_fixed.epub
```
