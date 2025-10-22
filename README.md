# EPUB Master Fixer - Ultra-Minimal Toolkit

## 🎯 Essential Scripts (3 Total)

### 🔧 **Primary Tools**
- `epub_master_fixer.py` - All-in-one EPUB fixing tool
- `validate_epub.py` - Simple validation utility

### 📦 **Basic Utilities** 
- `epubcheck.jar` - EPUB validation library

## 🚀 Quick Start

```bash
# Fix EPUB validation errors
python epub_master_fixer.py book.epub

# Validate EPUB
python validate_epub.py book.epub
```

## 📊 What It Fixes

### ✅ **EPUB 2.0.1 Compatibility**
- Removes EPUB3-specific elements (epub:type, aria, role)
- Converts HTML5→HTML4 (section→div, nav→div, figure→div)
- Fixes charset and meta tags

### 🔗 **Fragment Identifiers**
- Fixes broken internal links and TOC references
- Validates anchor targets
- Removes dead fragment links

### 🏗️ **Structure Fixes**
- Proper mimetype handling
- Correct EPUB packaging
- XML/HTML syntax validation

## 🗂️ **Archive**
60+ redundant scripts moved to `./archive/` folder

## 📝 Simple Usage

```bash
# Basic workflow
python epub_master_fixer.py mybook.epub
python validate_epub.py mybook.epub

# Creates automatic backup: mybook_backup.epub
```

## 🔍 Validation Output
- ✅ **Green**: Valid EPUB
- ❌ **Red**: Errors found  
- 📊 **Numbers**: Error/warning counts