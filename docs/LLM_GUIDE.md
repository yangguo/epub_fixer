# EPUB Agent System with Claude LLM Brain 🧠

An intelligent EPUB processing system that uses Claude AI as its "brain" to analyze, diagnose, and fix EPUB validation errors.

## Features

### Traditional Mode (Rule-Based)
- ✅ Validates EPUB files using epubcheck
- ✅ Fixes common EPUB errors automatically
- ✅ DRM removal and font deobfuscation
- ✅ NCX navigation fixes
- ✅ HTML/XML structure repairs

### LLM-Powered Mode (Intelligent) 🚀
- 🧠 **AI Error Analysis**: Claude analyzes epubcheck output to understand root causes
- 🎯 **Smart Workflow Optimization**: AI decides the best sequence of fixing steps
- 💡 **Intelligent Suggestions**: Get AI recommendations for complex errors
- 📊 **Detailed Insights**: Understand what's wrong and how to fix it
- 🔄 **Adaptive Recovery**: AI suggests recovery strategies when fixes fail

## Installation

1. **Install Python dependencies:**
```bash
# Option 1: Using venv (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Option 2: User install (if venv not available)
pip install --user anthropic python-dotenv
```

2. **Set up your Anthropic API key:**
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API key
# Get your key from: https://console.anthropic.com/
```

3. **Ensure Java is installed** (for epubcheck):
```bash
java -version  # Should be Java 8 or higher
```

## Usage

### Basic Usage (Rule-Based)
```bash
# Validate and fix an EPUB
python epub_agent_cli.py mybook.epub

# Specify output file
python epub_agent_cli.py mybook.epub -o fixed.epub
```

### LLM-Powered Usage (Intelligent) 🧠
```bash
# Use Claude LLM brain for intelligent processing
python epub_agent_cli.py mybook.epub --llm

# With custom output and API key
python epub_agent_cli.py mybook.epub -o fixed.epub --llm --api-key sk-xxx

# Verbose mode to see LLM insights
python epub_agent_cli.py mybook.epub --llm -v
```

### Advanced Workflows
```bash
# Include DRM removal
python epub_agent_cli.py encrypted.epub --llm --drm

# Custom workflow
python epub_agent_cli.py mybook.epub --llm --workflow validation fixing validation

# Let AI optimize the workflow (interactive)
python epub_agent_cli.py mybook.epub --llm
# AI will analyze errors and suggest optimal workflow
```

## How the LLM Brain Works

### 1. Error Analysis
Claude reads the epubcheck output and provides:
- Error count and categorization
- Severity assessment (critical/high/medium/low)
- Root cause analysis
- Fixability assessment

### 2. Workflow Optimization
The AI determines the optimal sequence of agents based on:
- Error types detected
- Complexity of issues
- Dependencies between fixes

### 3. Intelligent Fixing
During the fixing phase, the AI:
- Suggests specific repair strategies
- Identifies risky operations
- Recommends validation points

### 4. Failure Recovery
If a fix fails, the AI:
- Analyzes what went wrong
- Suggests alternative approaches
- Recommends manual intervention if needed

## Architecture

```
┌─────────────────────┐
│   LLM Brain         │
│   (Claude)          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Orchestrator      │
│   (Workflow Engine) │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    ▼             ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Validation│───│ Fixing  │───│Validation│
│  Agent  │   │  Agent  │   │  Agent  │
└─────────┘   └─────────┘   └─────────┘
```

### Agents
- **ValidationAgent**: Runs epubcheck, uses LLM to analyze results
- **FixingAgent**: Applies fixes, gets LLM strategy recommendations
- **DRMRemovalAgent**: Removes DRM/deobfuscates fonts
- **Orchestrator**: Coordinates workflow with LLM insights

### LLM Brain Capabilities
- `analyze_epub_errors()`: Parse and understand validation output
- `decide_workflow()`: Choose optimal agent sequence
- `generate_fix_strategy()`: Create specific repair plans
- `extract_error_details()`: Get structured error information
- `ask_question()`: General Q&A about EPUB issues

## Example Output

```
🧠 Initializing Claude LLM brain...
✓ LLM brain initialized

🤔 Analyzing optimal workflow...
📊 LLM Analysis: EPUB has 47 errors primarily related to invalid NCX identifiers and unclosed HTML tags
   Severity: HIGH
   Fixable: Yes

💡 LLM suggests workflow: validation -> fixing -> validation
   Use LLM-suggested workflow? [Y/n]: y
   ✓ Using LLM-optimized workflow

🔧 Building workflow: validation -> fixing -> validation

🚀 Starting EPUB processing...

============================================================
📋 EPUB AGENT SYSTEM RESULTS
============================================================
Input:  mybook.epub
Status: ✓ SUCCESS
Output: mybook_fixed.epub

📝 WORKFLOW EXECUTION:

✓ VALIDATION
   Errors: 47, Warnings: 3
   LLM: High-severity issues with NCX and HTML structure

✓ FIXING
   LLM: Applied NCX identifier fixes and HTML tag repairs

✓ VALIDATION
   Errors: 0, Warnings: 2
   LLM: All critical errors resolved
```

## Configuration

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-...          # Your Claude API key (required for LLM)
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Model to use (optional)
ANTHROPIC_BASE_URL=https://...    # Custom API endpoint (optional)
```

### Command-Line Options
```bash
--llm                    # Enable LLM mode
--api-key KEY           # Anthropic API key
--model NAME            # Model name (e.g., claude-3-opus-20240229)
--base-url URL          # Custom API base URL
-v, --verbose           # Verbose output
-o, --output FILE       # Output file path
-w, --workflow AGENTS   # Custom workflow
--drm                   # Include DRM removal
```

### Available Models
- `claude-3-5-sonnet-20241022` (default, recommended)
- `claude-3-opus-20240229` (most capable)
- `claude-3-haiku-20240307` (fastest, cheapest)

See `LLM_CONFIG.md` for advanced configuration options.

## API Cost Estimates

The LLM brain makes approximately:
- **With --llm**: 2-4 API calls per run
- **Per validation**: ~1,000-2,000 tokens (analysis)
- **Per workflow decision**: ~500-1,000 tokens
- **Estimated cost**: $0.01-0.05 per EPUB (using Claude 3.5 Sonnet)

## Troubleshooting

### LLM brain fails to initialize
```bash
# Check API key
echo $ANTHROPIC_API_KEY

# Test with explicit key
python epub_agent_cli.py mybook.epub --llm --api-key sk-your-key
```

### Import errors
```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Check Python path
python -c "import anthropic; print('OK')"
```

### Java not found
```bash
# Install Java (Ubuntu/Debian)
sudo apt install default-jdk

# Install Java (macOS)
brew install openjdk
```

## Development

### Adding New Agents
1. Create agent class inheriting from `BaseAgent`
2. Implement `run()` method
3. Add to `AGENT_MAPPING` in `config.py`
4. Use `self.llm_brain` for AI capabilities

```python
class MyAgent(BaseAgent):
    def __init__(self, llm_brain=None):
        super().__init__("my_agent", llm_brain)
    
    def run(self):
        if self.llm_brain:
            advice = self.llm_brain.ask_question("How should I process this?")
        # Your logic here
        return self.result
```

### Testing
```bash
# Test without LLM (rule-based)
python epub_agent_cli.py test.epub

# Test with LLM
python epub_agent_cli.py test.epub --llm -v
```

## License

MIT

## Credits

- **epubcheck**: EPUB validation engine
- **Anthropic Claude**: LLM brain
- **DeDRM Tools**: DRM removal techniques
