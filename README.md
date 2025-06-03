# EPUB Fixer Toolkit

A comprehensive collection of Python tools for fixing EPUB validation errors and ensuring EPUB 2/3 compatibility.

## 🚀 Quick Start

### Prerequisites
- Python 3.6+
- Java Runtime Environment (for epubcheck)
- `epubcheck.jar` (included)

### Basic Usage

```bash
# Fix EPUB with comprehensive validation
python fix_epub.py --version epub3 --file your_book.epub

# Quick fix with predefined settings
python comprehensive_fix.py
```

## 📁 Project Structure

### Core Tools

- **`fix_epub.py`** - Advanced EPUB validation fixer with iterative error correction
- **`comprehensive_fix.py`** - Batch EPUB processor for common issues
- **`repack_epub.py`** - EPUB repacking utility

### Utilities

- **`convert_epub3_to_epub2.py`** - EPUB 3 to EPUB 2 conversion
- **`improved_remove_drm.py`** - DRM removal tool
- **`restore_filename_drm_solution.py`** - Filename restoration utility
- **`check_epub_simple.bat`** - Windows batch script for quick validation

### Dependencies

- **`epubcheck.jar`** - Official EPUB validation tool
- **`lib/`** - Java dependencies for epubcheck

## 🛠️ Main Tools

### fix_epub.py - Advanced EPUB Fixer

**Features:**
- Iterative error fixing with epubcheck validation
- Support for both EPUB 2 and EPUB 3
- Comprehensive error handling (20+ fix functions)
- Command-line interface with progress tracking

**Usage:**
```bash
# Fix for EPUB 3 (default)
python fix_epub.py --file book.epub

# Fix for EPUB 2 compatibility
python fix_epub.py --version epub2 --file book.epub
```

**Fixes Applied:**
- Role attributes and ARIA labels
- Section element conversion
- Body structure issues
- H1 element placement
- Malformed XML syntax
- Charset encoding issues
- Meta tag formatting
- Fragment identifiers
- CSS reference problems

### comprehensive_fix.py - Batch Processor

**Features:**
- Single-pass EPUB processing
- Creates missing CSS files
- Fixes content.opf metadata
- Applies comprehensive XHTML fixes

**Usage:**
```bash
python comprehensive_fix.py
```

**Typical Workflow:**
1. Extract EPUB
2. Create missing CSS files
3. Fix content.opf issues
4. Apply XHTML fixes
5. Repack EPUB

## 🔧 Common Fix Categories

### Meta Tag Issues
- Malformed charset declarations
- Line breaks in meta tags
- Missing or extra brackets
- Spacing issues
- Self-closing tag problems

### Structure Issues
- Incomplete body elements
- Malformed div and paragraph tags
- Missing closing brackets
- Invalid nesting

### EPUB Compatibility
- EPUB 3 to EPUB 2 conversion
- Role attribute removal
- Section to div conversion
- ARIA label handling

### Content Issues
- Fragment identifier problems
- Missing CSS file references
- Broken internal links
- Encoding problems

## 📋 Validation Workflow

1. **Initial Validation**: Run epubcheck to identify errors
2. **Iterative Fixing**: Apply fixes based on error types
3. **Re-validation**: Check if errors are resolved
4. **Repeat**: Continue until EPUB passes validation
5. **Final Output**: Generate clean, validated EPUB

## 🎯 Error Types Handled

- **RSC-005**: Invalid XML syntax
- **RSC-012**: Fragment identifier issues
- **RSC-016**: Missing files
- **HTM-009**: Invalid HTML structure
- **CSS-008**: CSS reference problems
- **OPF-007**: Metadata issues
- **And many more...**

## 📝 Configuration

### Default Settings
- Maximum iterations: 10
- Target version: EPUB 3
- Output validation: Enabled
- Progress reporting: Enabled

### Customization
Modify the main functions in each script to adjust:
- File paths
- Iteration limits
- Fix priorities
- Output formats

## 🚨 Important Notes

### File Handling
- Always backup original EPUB files
- Tools create `_fixed` versions by default
- Temporary directories are cleaned up automatically

### Java Dependencies
- Ensure Java is installed and accessible
- `epubcheck.jar` must be in the project directory
- All required JAR files are included in `lib/`

### Windows Users
- Use `check_epub_simple.bat` for quick validation
- PowerShell or Command Prompt supported
- File paths use Windows separators

## 🔍 Troubleshooting

### Common Issues

**"Java not found"**
- Install Java Runtime Environment
- Ensure `java` command is in PATH

**"epubcheck.jar not found"**
- Verify `epubcheck.jar` is in project directory
- Check file permissions

**"Encoding errors"**
- Ensure EPUB files use UTF-8 encoding
- Check for special characters in file paths

**"Validation still fails"**
- Some errors require manual intervention
- Check epubcheck output for specific guidance
- Consider EPUB structure limitations

## 📚 Additional Resources

- [EPUB Specification](https://www.w3.org/publishing/epub3/)
- [EPUBCheck Documentation](https://github.com/w3c/epubcheck)
- [EPUB Accessibility Guidelines](https://www.w3.org/publishing/a11y/)

## 🤝 Contributing

To add new fix functions:
1. Add function to `fix_epub.py`
2. Import in `comprehensive_fix.py` if needed
3. Update error handling logic
4. Test with various EPUB files

## 📄 License

This project is provided as-is for EPUB processing and validation purposes.

---

**Note**: Always test with sample files before processing important EPUB collections. Some fixes may alter content structure or formatting.