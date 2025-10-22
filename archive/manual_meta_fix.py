#!/usr/bin/env python3
"""
Manual meta tag reconstruction for EPUB validation
"""

import os
import re
import zipfile
import subprocess

def fix_meta_tags_manual(content):
    """
    Manually fix meta tags by reconstructing them properly
    """
    fixes = 0
    
    # Pattern 1: Fix Content-Type meta tags specifically
    # Look for the problematic pattern and replace it entirely
    pattern1 = r'<meta\s+http-equiv="Content-Type"\s+content="text/html;\s*charset="utf-8"\s*/?>'
    replacement1 = '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
    
    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        fixes += 1
        print("Fixed Content-Type meta tag")
    
    # Pattern 2: Fix any meta tag that doesn't end properly
    # This catches meta tags that might have malformed endings
    pattern2 = r'<meta([^>]*?)>(?!\s*</meta>)'
    def fix_meta_ending(match):
        attrs = match.group(1).strip()
        if not attrs.endswith('/'):
            return f'<meta{attrs} />'
        return match.group(0)
    
    original_content = content
    content = re.sub(pattern2, fix_meta_ending, content)
    if content != original_content:
        fixes += 1
        print("Fixed meta tag endings")
    
    # Pattern 3: Fix specific charset patterns that might be malformed
    pattern3 = r'charset="([^"]+)"\s*([^/>]*?)\s*/?\s*>'
    def fix_charset_ending(match):
        charset_value = match.group(1)
        remaining = match.group(2).strip()
        if remaining:
            return f'charset="{charset_value}" {remaining} />'
        else:
            return f'charset="{charset_value}" />'
    
    # Apply this only to lines containing charset
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'charset=' in line and '<meta' in line:
            original_line = line
            # Reconstruct the entire meta tag
            if 'Content-Type' in line:
                # Extract the charset value
                charset_match = re.search(r'charset="([^"]+)"', line)
                if charset_match:
                    charset_val = charset_match.group(1)
                    # Reconstruct the entire line with proper indentation
                    indent = len(line) - len(line.lstrip())
                    new_line = ' ' * indent + f'<meta http-equiv="Content-Type" content="text/html; charset="{charset_val}" />'
                    lines[i] = new_line
                    if new_line != original_line:
                        fixes += 1
                        print(f"Reconstructed line: '{original_line.strip()}' -> '{new_line.strip()}'")
    
    return '\n'.join(lines), fixes

def process_epub_manual_fix(input_path, output_path):
    """
    Process EPUB with manual meta tag fixes
    """
    total_fixes = 0
    
    # Extract EPUB
    extract_dir = 'manual_fix_temp'
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
                    
                    fixed_content, fixes = fix_meta_tags_manual(content)
                    
                    if fixes > 0:
                        with open(file_path, 'w', encoding='utf-8', newline='\n') as f:
                            f.write(fixed_content)
                        total_fixes += fixes
                        print(f"Fixed {fixes} issues in {file}")
                
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
        errors = output.count('ERROR') - fatal_errors
        
        return output, fatal_errors, errors
    
    except Exception as e:
        return f"Error running epubcheck: {e}", 0, 0

def main():
    input_epub = 'doing2_ultimate_fixed.epub'
    output_epub = 'doing2_manual_fixed.epub'
    validation_file = 'manual_validation.txt'
    
    if not os.path.exists(input_epub):
        print(f"Input file {input_epub} not found!")
        return
    
    print("Starting manual meta tag fix...")
    
    # Process the EPUB
    fixes_applied = process_epub_manual_fix(input_epub, output_epub)
    
    print(f"\nApplied {fixes_applied} fixes. Running validation...")
    
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
    elif fatal_errors == 0:
        print(f"\n✅ No fatal errors! Only {errors} regular errors remain")
    else:
        print(f"\n⚠️  Still has {fatal_errors} fatal errors and {errors} regular errors")

if __name__ == '__main__':
    main()