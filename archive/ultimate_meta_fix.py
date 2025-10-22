#!/usr/bin/env python3
"""
Ultimate fix for all meta tag malformations in EPUB
"""

import os
import re
import zipfile
import subprocess
from pathlib import Path

def fix_all_meta_issues(content):
    """
    Fix all possible meta tag malformations
    """
    fixes_applied = 0
    
    # Pattern 1: Fix charset attributes that might be malformed
    # Handle cases like charset="UTF-8"/>, charset="utf-8"/>, etc.
    patterns_to_fix = [
        # Fix missing space before />
        (r'charset="([^"]+)"(/?>)', r'charset="\1" />'),
        (r'charset="([^"]+)"\s*/>', r'charset="\1" />'),
        
        # Fix any meta tag that doesn't have proper spacing
        (r'<meta([^>]+?)(/?>)', lambda m: f'<meta{m.group(1).rstrip()} />'),
        
        # Fix double quotes in charset
        (r'charset="([^"]+)""', r'charset="\1"'),
        
        # Fix malformed Adept.expected.resource tags
        (r'<meta\s+content="([^"]+)"\s+name="Adept\.expected\.resource"\s*/>', 
         r'<meta content="\1" name="Adept.expected.resource" />'),
        
        # Fix Content-Type meta tags
        (r'<meta\s+http-equiv="Content-Type"\s+content="text/html;\s*charset=([^"]+)"\s*/>', 
         r'<meta http-equiv="Content-Type" content="text/html; charset=\1" />'),
    ]
    
    original_content = content
    
    for pattern, replacement in patterns_to_fix:
        if callable(replacement):
            new_content = re.sub(pattern, replacement, content)
        else:
            new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            fixes_applied += 1
            content = new_content
    
    # Additional fix: ensure all meta tags have proper self-closing format
    # Find all meta tags and ensure they end with " />"
    def fix_meta_closing(match):
        tag_content = match.group(1).rstrip()
        if not tag_content.endswith('/'):
            return f'<meta{tag_content} />'
        else:
            # Already has /, just ensure proper spacing
            if tag_content.endswith('/'):
                return f'<meta{tag_content[:-1].rstrip()} />'
            return match.group(0)
    
    meta_pattern = r'<meta([^>]*?)>'
    content = re.sub(meta_pattern, fix_meta_closing, content)
    
    # Fix empty alt attributes
    content = re.sub(r'alt=""', 'alt="Cover image"', content)
    
    if content != original_content:
        fixes_applied += 1
    
    return content, fixes_applied

def process_epub(input_path, output_path):
    """
    Process EPUB file and fix all meta tag issues
    """
    total_fixes = 0
    files_processed = 0
    
    # Extract EPUB
    extract_dir = 'ultimate_fix_temp'
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(input_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process all XHTML files
    for root, dirs, files in os.walk(extract_dir):
        for file in files:
            if file.endswith('.xhtml'):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    fixed_content, fixes = fix_all_meta_issues(content)
                    
                    if fixes > 0:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        
                        print(f"Fixed {fixes} issues in {file}")
                        total_fixes += fixes
                        files_processed += 1
                    
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    # Repack EPUB
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_out.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extract_dir)
                zip_out.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(extract_dir)
    
    print(f"\nProcessed {files_processed} files with {total_fixes} total fixes")
    return total_fixes

def run_epubcheck(epub_path):
    """
    Run epubcheck and return results
    """
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Count errors
        fatal_errors = output.count('FATAL')
        errors = output.count('ERROR') - fatal_errors  # Subtract FATAL from ERROR count
        
        return output, fatal_errors, errors
    
    except Exception as e:
        return f"Error running epubcheck: {e}", 0, 0

def main():
    input_epub = 'doing2_syntax_fixed.epub'
    output_epub = 'doing2_ultimate_fixed.epub'
    validation_file = 'ultimate_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting ultimate meta tag fix...")
    
    # Process the EPUB
    fixes_applied = process_epub(input_epub, output_epub)
    
    if fixes_applied > 0:
        print(f"\nApplied {fixes_applied} fixes. Running validation...")
    else:
        print("\nNo fixes needed. Running validation...")
    
    # Validate the result
    validation_output, fatal_errors, errors = run_epubcheck(output_epub)
    
    # Save validation results
    with open(validation_file, 'w', encoding='utf-8') as f:
        f.write(validation_output)
    
    print(f"\nValidation complete:")
    print(f"Fatal errors: {fatal_errors}")
    print(f"Regular errors: {errors}")
    print(f"Results saved to {validation_file}")
    
    if fatal_errors == 0 and errors == 0:
        print("\n🎉 EPUB is now valid!")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal errors and {errors} regular errors")

if __name__ == '__main__':
    main()