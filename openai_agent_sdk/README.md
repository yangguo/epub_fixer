# OpenAI Agent SDK Variant

An alternate agent loop that uses the OpenAI Agents SDK with the rule-based EPUB fixer.

## Setup
- Install deps: `pip install -r requirements.txt`
- Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, `OPENAI_TEMPERATURE`,
  `OPENAI_AGENT_MAX_TURNS`, `OPENAI_BASE_URL`/`OPENAI_API_BASE`, `OPENAI_ORG`,
  `OPENAI_PROJECT`, `OPENAI_API_MODE=responses|chat_completions`)

## Run
```bash
python -m openai_agent_sdk.cli path/to/book.epub \
  --model gpt-4.1 \
  --output book_fixed.epub \
  --goal "Fix errors then revalidate"
```

Default workflow: validate → apply_rule_based_fix → validate. Tool calls use `agents.function_tool`
wrappers and the final reply comes from the Agent SDK loop. Use `--json` to print the raw response.

### Continuing until clean
- After the agent run, the CLI re-validates the EPUB. If errors remain, it keeps going by default.
- Follow-up attempts reuse the OpenAI Agents SDK loop with the same tools, up to `--max-followups`
  additional passes (or disable with `--no-continue`).
- The SDK package includes its own epubcheck runner and reuses the canonical rule-based fixer
  from `epub_master_fixer.py`, keeping EPUB 2/3 behavior consistent with the root CLI.
