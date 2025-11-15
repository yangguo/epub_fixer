# CustomFixAgent Current Logic

## Hybrid Approach: Rule-Based + LLM-Generated Fixes

The CustomFixAgent now uses two distinct fixing strategies, depending on the situation:

### 1. Rule-Based Fixes (Hardcoded)
**Purpose**: Fix common, well-known issues quickly and reliably.  
**Triggered When**:
- LLM error extraction fails (invalid JSON response).
- The error is specifically identified as a missing `<body>` tag.

**How It Works**:
1. Extracts the EPUB into a temporary directory.
2. Scans all HTML/XHTML files.
3. For each file with `<body>` but no `</body>`:
   - Inserts `</body>` before the closing `</html>` tag.
4. Repacks the EPUB.

**Examples**:
- Missing `<body>` tags (your current issue).
- Missing `<html>` tags (future extension).

### 2. LLM-Generated Fixes (Adaptive)
**Purpose**: Fix complex, unknown issues using AI intelligence.  
**Triggered When**:
- LLM error extraction works correctly.
- The error is not covered by rule-based fixes.

**How It Works**:
1. Extracts the EPUB into a temporary directory.
2. Gets detailed error analysis from LLM.
3. Generates fix instructions for each error:
   - Regex patterns (for tag fixes).
   - Content edits (for structural fixes).
   - XML modifications (for metadata issues).
4. Applies fixes directly to extracted files.
5. Repacks the EPUB.

**Examples**:
- Unclosed `<div>` tags with complex nesting.
- Invalid XML namespaces.
- Broken NCX navigation structures.

## File Modification Process
In **both cases**, the agent:
- **Modifies extracted files directly** in the temporary directory.
- **Creates a backup** of the original EPUB before replacing it.
- **Repacks** the fixed files into a valid EPUB.

## Why This Hybrid Approach Works
| Feature | Rule-Based | LLM-Generated |
|---------|------------|---------------|
| Speed | Fast | Medium |
| Reliability | High | High (for valid LLM responses) |
| Flexibility | Low (covers specific issues) | High (handles any issue) |
| Cost | Free | Uses LLM tokens |

## Your Specific Case
For your 16 missing `<body>` tag errors, the agent will use the **rule-based fallback** because:
1. The LLM error extraction was failing.
2. It directly detects the missing `<body>` tags by scanning files.

The fix is fast, reliable, and targeted to your exact issue!
