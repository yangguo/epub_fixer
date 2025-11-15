# LLM Configuration Guide

## Environment Variables

The LLM brain can be configured via environment variables in your `.env` file or via command-line arguments.

### Basic Configuration

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-xxxxx
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

### Custom API Endpoint

For using proxies, OpenRouter, or other Claude-compatible endpoints:

```bash
# .env file
ANTHROPIC_API_KEY=sk-xxxxx
ANTHROPIC_BASE_URL=https://your-proxy.com/v1
```

## Command-Line Options

Override environment variables with CLI flags:

```bash
# Custom model
python3 epub_agent_cli.py mybook.epub --llm --model claude-3-opus-20240229

# Custom API endpoint
python3 epub_agent_cli.py mybook.epub --llm \
  --api-key sk-xxxxx \
  --base-url https://api.openrouter.ai/api/v1

# All options combined
python3 epub_agent_cli.py mybook.epub --llm \
  --api-key sk-xxxxx \
  --model claude-3-5-sonnet-20241022 \
  --base-url https://your-proxy.com/v1 \
  -o fixed.epub -v
```

## Available Models

### Anthropic Claude Models
- `claude-3-5-sonnet-20241022` (default, recommended)
- `claude-3-5-sonnet-20240620`
- `claude-3-opus-20240229` (most capable, slower)
- `claude-3-sonnet-20240229`
- `claude-3-haiku-20240307` (fastest, cheaper)

### Through OpenRouter
When using OpenRouter as base URL:
- `anthropic/claude-3.5-sonnet`
- `anthropic/claude-3-opus`
- Other compatible models

## Custom API Endpoints

### OpenRouter

```bash
# .env
ANTHROPIC_API_KEY=sk-or-xxxxx  # OpenRouter API key
ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
CLAUDE_MODEL=anthropic/claude-3.5-sonnet
```

### Local Proxy

For running through a local proxy (e.g., for caching or monitoring):

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_BASE_URL=http://localhost:8080/v1
```

### Corporate Proxy

For enterprise environments with proxy servers:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_BASE_URL=https://proxy.company.com/anthropic/v1
```

## Configuration Priority

Settings are applied in this order (highest priority first):

1. **Command-line arguments** (--api-key, --model, --base-url)
2. **Environment variables** (ANTHROPIC_API_KEY, CLAUDE_MODEL, ANTHROPIC_BASE_URL)
3. **Defaults** (claude-3-5-sonnet-20241022)

## Examples

### Example 1: Using Different Models

```bash
# Fast and cheap (haiku)
python3 epub_agent_cli.py book.epub --llm --model claude-3-haiku-20240307

# Most capable (opus)
python3 epub_agent_cli.py book.epub --llm --model claude-3-opus-20240229

# Default (sonnet 3.5)
python3 epub_agent_cli.py book.epub --llm
```

### Example 2: OpenRouter Setup

```bash
# Set environment
export ANTHROPIC_API_KEY=sk-or-v1-xxxxx
export ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
export CLAUDE_MODEL=anthropic/claude-3.5-sonnet

# Run
python3 epub_agent_cli.py mybook.epub --llm
```

### Example 3: Testing Different Endpoints

```bash
# Test with standard Anthropic API
python3 epub_agent_cli.py test.epub --llm

# Test with custom proxy
python3 epub_agent_cli.py test.epub --llm \
  --base-url http://localhost:8080/v1

# Test with OpenRouter
python3 epub_agent_cli.py test.epub --llm \
  --base-url https://openrouter.ai/api/v1 \
  --api-key sk-or-xxxxx
```

## Troubleshooting

### "Connection failed"
- Check your base URL is correct
- Verify network connectivity
- Ensure proxy/firewall allows the connection

### "Invalid API key"
- For custom endpoints, ensure the key format matches
- OpenRouter keys start with `sk-or-`
- Anthropic keys start with `sk-ant-`

### "Model not found"
- Verify model name matches the endpoint
- Anthropic: use full model IDs (e.g., `claude-3-5-sonnet-20241022`)
- OpenRouter: use provider prefix (e.g., `anthropic/claude-3.5-sonnet`)

### "Rate limit exceeded"
- Switch to a different model tier
- Add delays between requests
- Use a proxy with rate limiting

## Advanced: Custom Provider Implementation

If you're using a Claude-compatible API (like a custom wrapper), ensure it:

1. Accepts the same message format as Anthropic's API
2. Returns responses in the same JSON structure
3. Supports the `/v1/messages` endpoint
4. Handles the same authentication scheme

Example compatible API:
```python
# Your custom endpoint should accept:
POST /v1/messages
Headers:
  x-api-key: your-api-key
  anthropic-version: 2023-06-01
Body:
  {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2000,
    "messages": [...]
  }
```

## Cost Optimization

### Model Selection by Task

```bash
# For simple error analysis (cheap)
--model claude-3-haiku-20240307

# For complex EPUB issues (balanced)
--model claude-3-5-sonnet-20241022  # Default

# For very difficult cases (expensive but best)
--model claude-3-opus-20240229
```

### Estimated Costs (Anthropic Pricing)

- **Haiku**: ~$0.001-0.003 per EPUB
- **Sonnet 3.5**: ~$0.01-0.05 per EPUB (default)
- **Opus**: ~$0.05-0.15 per EPUB

*Costs vary based on error complexity and number of LLM calls*

## Environment File Template

Complete `.env` template with all options:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional - Model Selection
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Optional - Custom Endpoint
# ANTHROPIC_BASE_URL=https://api.anthropic.com

# Optional - Proxy Settings (if needed)
# HTTP_PROXY=http://proxy.company.com:8080
# HTTPS_PROXY=http://proxy.company.com:8080

# For OpenRouter
# ANTHROPIC_API_KEY=sk-or-xxxxx
# ANTHROPIC_BASE_URL=https://openrouter.ai/api/v1
# CLAUDE_MODEL=anthropic/claude-3.5-sonnet
```
