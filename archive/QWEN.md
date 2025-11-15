# EPUB Master Fixer - Project Context

## Project Overview

This is a specialized Python toolkit for EPUB file validation and repair, designed to fix common EPUB validation errors and ensure compatibility across different EPUB readers. The project has been streamlined from 60+ scripts to a focused set of essential tools that handle 95% of EPUB validation issues.

**Main Purpose**: Automatically fix EPUB validation errors detected by epubcheck, converting EPUB 3 files to EPUB 2.0.1 compatibility and repairing structural issues.

## Core Architecture

### Primary Tools

1. **epub_master_fixer.py** - The main all-in-one fixing tool
   - Iterative validation and fixing (up to 5 iterations)
   - Handles EPUB 2.0.1 compatibility
   - Fixes fragment identifiers, dir attributes, and HTML structure
   - Creates automatic backups

2. **validate_epub.py** - Simple validation utility
   - Quick validation using epubcheck
   - Error and warning counting
   - Clean output formatting

3. **fix_meta_and_fragments.py** - Specialized fixer
   - Targeted fixes for metadata and fragment issues
   - Complementary to the master fixer

### Supporting Files

- **epubcheck.jar** - Official EPUB validation tool (Java-based)
- **check_epub_simple.bat** - Windows batch script for quick validation
- **lib/** - Java dependencies for epubcheck

### Archive Directory

Contains 60+ legacy scripts that have been consolidated into the main tools. Preserved for historical reference and potential specialized use cases.

## Key Technologies

- **Python 3.6+** - Primary development language
- **Java Runtime** - Required for epubcheck.jar
- **ZIP manipulation** - EPUB files are ZIP archives with specific structure
- **XML/HTML parsing** - EPUB content is primarily XHTML
- **Regular expressions** - Pattern-based fixing of common issues

## Building and Running

### Prerequisites
```bash
# Python 3.6+ required
python --version

# Java Runtime Environment required for epubcheck
java -version

# epubcheck.jar must be present in project root
ls epubcheck.jar
```

### Core Commands

```bash
# Fix EPUB validation errors (primary workflow)
python epub_master_fixer.py book.epub

# Quick validation only
python validate_epub.py book.epub

# Windows batch validation
check_epub_simple.bat book.epub

# Targeted meta/fragment fixes
python fix_meta_and_fragments.py book.epub
```

### Expected Behavior

1. **Master Fixer Workflow**:
   - Creates backup: `book_backup.epub`
   - Runs iterative validation (max 5 iterations)
   - Fixes 32+ files typically
   - Outputs validation results to `output.txt`

2. **Validation Output**:
   - ✅ Green text: Valid EPUB
   - ❌ Red text: Errors found
   - 📊 Numbers: Error/warning counts

## Development Conventions

### Code Style
- Python 3.6+ compatibility
- Comprehensive docstrings for all functions
- Error handling with try/catch blocks
- Progress reporting with print statements
- Temporary directory cleanup using context managers

### File Organization
- Main tools in project root
- Archive/ for legacy code
- lib/ for Java dependencies
- .gitignore excludes EPUB files and generated outputs

### Fixing Strategy
1. Extract EPUB to temporary directory
2. Apply pattern-based fixes using regex
3. Validate with epubcheck
4. Repack with proper mimetype handling
5. Repeat until valid or max iterations reached

### Common Fix Patterns
- EPUB 3 → EPUB 2 conversion (remove epub:type, aria, role)
- HTML5 → HTML4 (section→div, nav→div, figure→div)
- XML syntax fixes (malformed meta tags, charset issues)
- Fragment identifier validation
- Dir attribute correction (ltr/rtl only)

## Testing

No formal test suite exists. Testing is done by:
1. Running tools on problematic EPUB files
2. Checking epubcheck validation results
3. Verifying EPUB functionality in readers

## Project History

Originally contained 60+ specialized scripts for different EPUB issues. Refactored into a streamlined toolkit focusing on the most common validation problems. The archive preserves the extensive development history and specialized tools that may be needed for edge cases.

## Usage Notes

- Always creates backups before modifying files
- Works best with EPUB 3 files needing EPUB 2 compatibility
- Requires Java for epubcheck functionality
- Handles most common validation errors automatically
- Some edge cases may require manual intervention