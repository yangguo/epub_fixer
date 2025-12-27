# Vercel Node Agent

Node-based Vercel function that runs the EPUB fixer with either OpenAI tool calls or Claude tool
calls. This variant includes a full JavaScript port of the Python EPUB fixer, handling 95% of
common EPUB validation issues.

## What It Fixes

The EPUB fixer handles these common issues:
- **NCX Issues**: Identifier mismatch with OPF, invalid XML IDs (colons, numeric starts),
  playOrder conflicts
- **HTML Issues**: Unclosed anchor/p tags, invalid ID attributes, missing alt on images,
  HTML5→EPUB2 conversion
- **Structural Issues**: Misplaced elements, missing titles, empty body elements, broken fragment
  references
- **EPUB 2.0.1 Compatibility**: Removes epub:type, aria-*, role attributes; converts
  section/nav/figure to div
- **OPF Issues**: Invalid page-map attribute in spine, fragment identifiers in manifest
- **CSS Issues**: Invalid font references

## Deploying to Vercel
- Set project root to `vercel_node_agent/` and keep `vercel.json` committed.
- Environment:
  - `OPENAI_API_KEY` (for OpenAI path)
  - `ANTHROPIC_API_KEY` (for Claude path)
  - Optional: `OPENAI_MODEL`, `CLAUDE_MODEL`, `OPENAI_BASE_URL`, `MAX_RETURN_BYTES`
- Dependencies are in `package.json`; Vercel will install them automatically.

## API
POST `/api/agent`

```json
{
  "provider": "openai | claude",
  "epub_url": "https://example.com/book.epub",
  "epub_base64": "<base64 epub bytes>",
  "goal": "Fix and revalidate",
  "model": "gpt-4.1-mini",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "max_turns": 4,
  "output_name": "custom_fixed.epub",
  "return_base64": true,
  "validate": true
}
```

- Provide either `epub_url` or `epub_base64`.
- Local file paths are intentionally rejected to avoid server-side file disclosure.
- `model`: Override the default model (e.g., `gpt-4.1-mini`,
  `claude-3-5-sonnet-20241022`, or any compatible model name).
- `base_url`: Custom base URL for OpenAI-compatible APIs (e.g., Azure OpenAI, local models,
  or other providers).
- `api_key`: Override the environment API key for this request.
- `output_name`: Optional filename hint; output is written to temp storage and cleaned up
  after response.
- Validation checks structural integrity: `mimetype` content and `META-INF/container.xml`.
- The fixer applies comprehensive rule-based fixes ported from the Python epub_master_fixer.
- Base64 output is limited to `MAX_RETURN_BYTES` (default 5 MB).

Response:
```json
{
  "provider": "openai",
  "success": true,
  "output_path": "/tmp/epub-fixer/epub-123_fixed.epub",
  "agent_result": { "...": "LLM trace" },
  "fix_result": {
    "success": true,
    "fixes": ["Fixed: OEBPS/content.xhtml", "Fixed: OEBPS/toc.ncx"],
    "notes": ["Applied 2 fixes to EPUB files."]
  },
  "validation": { "...": "structural validation summary" },
  "output_base64": "<optional>",
  "output_truncated": false
}
```

`output_path` is a temporary server-side path and is removed after the response is sent.

## Web UI
- Static console at `index.html` (served from the project root) that posts to `/api/agent`.
- Choose provider, supply EPUB URL or upload a file, set goal/model/output name, toggle validation,
  and optionally get a base64 download link.

## Local smoke test
- Install deps: `npm install`
- Run a one-off request:
  ```bash
  curl -X POST http://localhost:3000/api/agent \
    -H "Content-Type: application/json" \
    -d '{"provider":"openai","epub_url":"https://example.com/book.epub"}'
  ```
- When testing locally without Vercel, start a simple server such as `npx serve .` or use your own
  Node handler with this API file.
