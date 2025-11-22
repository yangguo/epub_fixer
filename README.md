# EPUB Master Fixer

A comprehensive EPUB validation and repair toolkit with optional AI-powered fixing capabilities.

## 🎯 Core Tools

### **Primary Scripts**
- **`epub_master_fixer.py`** - Rule-based EPUB fixing tool (handles 95% of common issues)
- **`epub_agent_cli.py`** - Advanced agent system with optional Claude AI integration
- **`validate_epub.py`** - Simple EPUB validation utility

### **Supporting Files**
- `epubcheck.jar` - EPUB validation library (Java-based)
- `config.py` - Shared configuration
- `utils.py` - Shared utilities

## 🚀 Quick Start

### Basic Mode (Rule-Based Fixing)
```bash
# Fix common EPUB validation errors
python epub_master_fixer.py book.epub

# Validate an EPUB
python validate_epub.py book.epub

# Creates automatic backup: book_backup.epub
```

### Advanced Mode (AI-Powered)
```bash
# Enable AI-powered intelligent fixing
python epub_agent_cli.py book.epub --llm

# With DRM removal
python epub_agent_cli.py book.epub --llm --drm

# Custom workflow
python epub_agent_cli.py book.epub --llm --workflow validation custom_fixing validation
```

## 📊 What It Fixes

### ✅ **EPUB 2.0.1 Compatibility**
- Removes EPUB3-specific elements (epub:type, aria, role)
- Converts HTML5→HTML4 (section→div, nav→div, figure→div)
- Fixes charset and meta tags
- Corrects NCX navigation structure

### 🔗 **Fragment Identifiers & Links**
- Fixes broken internal links and TOC references
- Validates anchor targets
- Removes dead fragment links
- Repairs NCX playOrder conflicts

### 🏗️ **Structure & Syntax**
- Proper mimetype handling
- Correct EPUB packaging
- XML/HTML syntax validation
- Unclosed tag repairs
- ID attribute fixing

### 🔒 **DRM Removal** (Agent Mode Only)
- Font deobfuscation
- Encryption removal
- Reference updates

## 🧠 AI Features (Optional)

When using `--llm` flag with `epub_agent_cli.py`:
- **Intelligent Error Analysis**: AI understands root causes, not just symptoms
- **Custom Fix Generation**: Creates error-specific repair strategies
- **Workflow Optimization**: AI decides best sequence of fixing steps
- **Adaptive Recovery**: Switches strategies when standard fixes fail

See **[docs/LLM_GUIDE.md](docs/LLM_GUIDE.md)** for detailed AI setup and usage.

## 📁 Project Structure

```
epubcheck/
├── epub_master_fixer.py      # Main rule-based fixer
├── epub_agent_cli.py          # AI-powered agent CLI
├── validate_epub.py           # Validation utility
├── config.py                  # Shared configuration
├── utils.py                   # Shared utilities
├── requirements.txt           # Python dependencies
├── .env.example              # API key template
│
├── agent_system/             # Agent framework
│   ├── orchestrator.py       # Workflow orchestration
│   ├── llm_brain.py          # AI integration
│   ├── validation_agent.py   # Validation agent
│   ├── fixing_agent.py       # Fixing agent
│   ├── custom_fix_agent.py   # AI-powered fixes
│   └── drm_agent.py          # DRM removal
│
├── docs/                     # Documentation
│   └── LLM_GUIDE.md          # AI features guide
│
├── archive/                  # Old/deprecated files
└── scripts/                  # Helper scripts
```

## 🔧 Installation

1. **Requirements:**
   - Python 3.9+
   - Java 8+ (for epubcheck)
   - Anthropic API key (optional, for AI features)

2. **Setup:**
   ```bash
   pip install -r requirements.txt
   ```

3. **For AI Features (Optional):**
   ```bash
   # Copy environment template
   cp .env.example .env
   
   # Edit .env and add your API key
   # ANTHROPIC_API_KEY=your-key-here
   ```

## 📝 Usage Examples

### Rule-Based Fixing
```bash
# Fix and validate
python epub_master_fixer.py mybook.epub
python validate_epub.py mybook_fixed.epub
```

### AI-Powered Fixing
```bash
# Let AI analyze and fix errors
python epub_agent_cli.py mybook.epub --llm --max-attempts 5

# Enable verbose mode for insights
python epub_agent_cli.py mybook.epub --llm -v
```

### OpenAI Agent SDK (Beta)
```bash
python -m openai_agent_sdk.cli mybook.epub \
  --model gpt-4.1 \
  --output mybook_fixed.epub
```
Uses the same rule-based fixer but routes decisions through the OpenAI Agents SDK (`openai-agents`
package with `function_tool` wrappers). Reads OpenAI settings from environment variables
(`OPENAI_API_KEY`, optional `OPENAI_BASE_URL`, `OPENAI_MODEL`, etc.). The CLI auto-validates after
the run and will reuse the OpenAI agent for follow-up passes until errors clear or `--max-followups`
is reached (`--no-continue` to disable). The OpenAI SDK package carries its own epubcheck runner
and rule-based fixer—no imports from the repo root.

## 🔍 Understanding Output

### Validation Results
- ✅ **Green/SUCCESS**: Valid EPUB, no errors
- ❌ **Red/ERROR**: Validation errors found
- ⚠️ **Yellow/WARNING**: Warnings (non-critical)
- 📊 **Numbers**: Error/warning counts

### Fix Results
- **Errors fixed**: Number of errors resolved
- **Remaining errors**: Issues that need manual review
- **Backup created**: Original file preserved as `*_backup.epub`

## 📚 Documentation

- **[docs/LLM_GUIDE.md](docs/LLM_GUIDE.md)** - AI features and setup
- **[archive/](archive/)** - Development history and references

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome!

## 📄 License

Free to use for personal and educational purposes.
