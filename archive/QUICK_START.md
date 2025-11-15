# Quick Start Guide

## Rule-Based Mode (No LLM Required)

### Basic Usage
```bash
# Fix an EPUB file
python3 epub_agent_cli.py mybook.epub

# Specify output file  
python3 epub_agent_cli.py mybook.epub -o fixed.epub
```

### What It Does
1. **Validates** the EPUB with epubcheck
2. **Fixes** common errors (NCX, HTML, XML issues)
3. **Validates** again to confirm fixes

### Example Output
```
🔧 Workflow: validation -> fixing -> validation

============================================================
Status: ✓ SUCCESS
Output: mybook_fixed.epub

📊 Results: 33 errors → 0 errors
   🎉 All errors fixed!

✓ validation
   Errors: 33, Warnings: 0

✓ fixing

✓ validation
   Errors: 0, Warnings: 0
```

## LLM-Powered Mode (Intelligent)

### Installation
```bash
# Install dependencies
pip install anthropic python-dotenv

# Set API key
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-...
```

### Usage
```bash
# Enable LLM brain
python3 epub_agent_cli.py mybook.epub --llm

# With custom API key
python3 epub_agent_cli.py mybook.epub --llm --api-key sk-xxx

# With custom model
python3 epub_agent_cli.py mybook.epub --llm --model claude-3-opus-20240229

# With custom API endpoint (proxy, OpenRouter, etc.)
python3 epub_agent_cli.py mybook.epub --llm --base-url https://api.openrouter.ai/api/v1

# Verbose mode (shows AI insights)
python3 epub_agent_cli.py mybook.epub --llm -v
```

### LLM Features
- 🧠 AI analyzes error patterns and root causes
- 🎯 Suggests optimal workflow based on issues
- 💡 Provides fixing recommendations
- 🔄 Offers recovery suggestions if fixes fail
- 📊 Explains what went wrong and why

### Example LLM Output
```
🧠 Initializing Claude LLM brain...
✓ LLM brain initialized

🤔 Analyzing optimal workflow...
📊 LLM Analysis: EPUB has NCX identifier mismatches and unclosed HTML tags
   Severity: HIGH
   Fixable: Yes

💡 LLM suggests workflow: validation -> fixing -> validation
   Use LLM-suggested workflow? [Y/n]: y
```

## Requirements

- **Python 3.7+**
- **Java** (for epubcheck)
- **Optional**: Anthropic API key (for LLM mode)

## Troubleshooting

### "Java not found"
Install Java:
```bash
# Ubuntu/Debian
sudo apt install default-jdk

# macOS
brew install openjdk
```

### "LLM brain failed"
Either:
1. Run without `--llm` flag (rule-based mode)
2. Check your `ANTHROPIC_API_KEY` in `.env`
3. Install: `pip install anthropic python-dotenv`

## Advanced

### Custom Workflows
```bash
# Skip initial validation
python3 epub_agent_cli.py mybook.epub -w fixing validation

# Include DRM removal
python3 epub_agent_cli.py mybook.epub --drm
```

### LLM Configuration
```bash
# Use different model
python3 epub_agent_cli.py mybook.epub --llm --model claude-3-haiku-20240307

# Use custom endpoint (OpenRouter, proxy, etc.)
python3 epub_agent_cli.py mybook.epub --llm \
  --base-url https://openrouter.ai/api/v1 \
  --api-key sk-or-xxxxx

# See LLM_CONFIG.md for detailed configuration options
```

### Available Agents
- `validation` - Run epubcheck
- `fixing` - Fix structural issues
- `drm_removal` - Remove DRM/deobfuscate fonts

## Files Created

- `mybook_fixed.epub` - Fixed EPUB file
- `mybook_fixed_backup.epub` - Backup of original
- `agent_system.log` - Detailed execution log

## More Info

See full documentation in `LLM_AGENT_README.md`
