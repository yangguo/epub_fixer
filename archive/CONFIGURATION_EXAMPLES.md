# Configuration Examples

Quick reference for common LLM configuration scenarios.

## Scenario 1: Standard Anthropic API

**Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
```

**Cost:** ~$0.01-0.05 per EPUB (Sonnet 3.5)

---

## Scenario 2: Cost Optimization (Haiku)

**Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-haiku-20240307
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
# OR override via CLI:
python3 epub_agent_cli.py mybook.epub --llm --model claude-3-haiku-20240307
```

**Cost:** ~$0.001-0.003 per EPUB (75% cheaper)

---

## Scenario 3: Maximum Quality (Opus)

**Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-opus-20240229
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
```

**Cost:** ~$0.05-0.15 per EPUB (most capable)

---

## Scenario 4: OpenRouter Integration

**Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-or-v1-xxxxx
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
CLAUDE_MODEL=anthropic/claude-3.5-sonnet
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
```

**Benefits:**
- Access to multiple providers
- Unified billing
- Fallback options

---

## Scenario 5: Corporate Proxy

**Setup:**
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_BASE_URL=https://ai-proxy.company.com/anthropic/v1

# Optional system proxy
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
```

**Benefits:**
- Compliance with corporate policies
- Centralized logging/monitoring
- Access control

---

## Scenario 6: Local Caching Proxy

**Setup:**

1. Run a local caching proxy (e.g., Helicone, LiteLLM):
```bash
# Example with LiteLLM proxy
litellm --model claude-3-5-sonnet-20241022 --port 8080
```

2. Configure client:
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_BASE_URL=http://localhost:8080/v1
```

**Usage:**
```bash
python3 epub_agent_cli.py mybook.epub --llm
```

**Benefits:**
- Response caching (save costs)
- Request monitoring
- Rate limiting

---

## Scenario 7: Testing Without API Calls

**Setup:**
```bash
# Don't set ANTHROPIC_API_KEY
# OR run without --llm flag
```

**Usage:**
```bash
# Rule-based mode (no LLM)
python3 epub_agent_cli.py mybook.epub
```

**Benefits:**
- No API costs
- Faster processing
- Works offline

---

## Scenario 8: Batch Processing with Cost Control

**Setup:**
```bash
# .env for production
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-haiku-20240307  # Cheaper model
```

**Script:**
```bash
#!/bin/bash
# batch_fix.sh

for epub in *.epub; do
    echo "Processing $epub..."
    python3 epub_agent_cli.py "$epub" --llm -o "fixed_$epub"
    sleep 2  # Rate limiting
done
```

**Usage:**
```bash
chmod +x batch_fix.sh
./batch_fix.sh
```

---

## Scenario 9: Development vs Production

**Development:**
```bash
# .env.development
ANTHROPIC_API_KEY=sk-ant-dev-xxxxx
CLAUDE_MODEL=claude-3-haiku-20240307
ANTHROPIC_BASE_URL=http://localhost:8080/v1  # Local mock
```

**Production:**
```bash
# .env.production
ANTHROPIC_API_KEY=sk-ant-prod-xxxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_BASE_URL=https://api.anthropic.com
```

**Usage:**
```bash
# Development
ln -sf .env.development .env
python3 epub_agent_cli.py test.epub --llm

# Production
ln -sf .env.production .env
python3 epub_agent_cli.py book.epub --llm
```

---

## Scenario 10: CLI Override for Quick Tests

**Setup:**
```bash
# .env has production settings
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

**Usage:**
```bash
# Quick test with cheaper model
python3 epub_agent_cli.py test.epub --llm --model claude-3-haiku-20240307

# Test with custom endpoint
python3 epub_agent_cli.py test.epub --llm \
  --base-url http://localhost:8080/v1

# Test with different API key
python3 epub_agent_cli.py test.epub --llm \
  --api-key sk-ant-test-xxxxx
```

---

## Configuration Priority Reference

```
Highest Priority
    ↓
1. CLI Arguments (--api-key, --model, --base-url)
2. Environment Variables (ANTHROPIC_API_KEY, CLAUDE_MODEL, ANTHROPIC_BASE_URL)
3. Defaults (claude-3-5-sonnet-20241022, https://api.anthropic.com)
    ↓
Lowest Priority
```

**Example:**
```bash
# .env
CLAUDE_MODEL=claude-3-haiku-20240307

# This overrides .env and uses opus:
python3 epub_agent_cli.py book.epub --llm --model claude-3-opus-20240229
```

---

## Troubleshooting Common Scenarios

### Can't connect to API
```bash
# Test connectivity
curl https://api.anthropic.com

# Check proxy settings
echo $HTTPS_PROXY

# Try with explicit URL
python3 epub_agent_cli.py book.epub --llm \
  --base-url https://api.anthropic.com
```

### API key not working
```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Test with explicit key
python3 epub_agent_cli.py book.epub --llm \
  --api-key sk-ant-xxxxx
```

### Model not found
```bash
# Check available models
# For Anthropic API: use full version IDs
--model claude-3-5-sonnet-20241022

# For OpenRouter: use provider prefix
--model anthropic/claude-3.5-sonnet
```

### Reduce costs
```bash
# Use cheaper model
--model claude-3-haiku-20240307

# Or disable LLM entirely
python3 epub_agent_cli.py book.epub  # No --llm flag
```

---

## See Also

- `LLM_CONFIG.md` - Detailed configuration guide
- `QUICK_START.md` - Quick reference
- `.env.example` - Template file
