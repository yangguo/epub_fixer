#!/usr/bin/env python3
import zipfile
import os
import re
import subprocess

def fix_html_content(content):
    """Fix malformed HTML content with comprehensive patterns"""
    lines = content.split('\n')
    
    for i, line in enumerate(lines):
        if i == 8:  # Line 9 (0-indexed)
            # Fix the specific malformed patterns on line 9
            
            # Fix missing quotes and malformed attributes
            line = re.sub(r'<body>\s*class="([^"]*?)"\s*id="([^"]*?)"', r'<body class="\1" id="\2"', line)
            
            # Fix malformed href attributes with missing quotes
            line = re.sub(r'href="([^"]*?)"([^>]*?)"<div', r'href="\1"><div', line)
            line = re.sub(r'href="([^"]*?)>"<div', r'href="\1"><div', line)
            
            # Fix class attributes with missing closing quotes
            line = re.sub(r'class=""([^>]*?)>', r'class="">\1', line)
            line = re.sub(r'class="([^"]*?)"([^>]*?)">', r'class="\1">\2', line)
            
            # Fix unclosed div tags by ensuring proper closure
            # Count opening and closing div tags
            open_divs = len(re.findall(r'<div[^>]*>', line))
            close_divs = len(re.findall(r'</div>', line))
            
            # Add missing closing div tags
            if open_divs > close_divs:
                missing_closes = open_divs - close_divs
                line += '</div>' * missing_closes
            
            # Fix unclosed body tags
            if '<body' in line and '</body>' not in line:
                line += '</body>'
            
            # Fix malformed anchor tags
            line = re.sub(r'<a\s+hr\s*ef=', r'<a href=', line)
            line = re.sub(r'<a\s+href="([^"]*?)"([^>]*?)"([^>]*?)>', r'<a href="\1">\2\3', line)
            
            # Fix incomplete tags
            line = re.sub(r'<(\w+)\s+([^>]*?)"<', r'<\1 \2"><', line)
            
            # Ensure all opening tags have proper closing
            line = re.sub(r'<(\w+)([^>]*?)"([^>]*?)$', r'<\1\2">\3', line)
            
            # Fix duplicate class attributes
            line = re.sub(r'class="([^"]*?)"\s+class="([^"]*?)"', r'class="\1 \2"', line)
            
            lines[i] = line
    
    return '\n'.join(lines)

def main():
    epub_file = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    print("Starting final HTML fix...")
    
    # Extract EPUB
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir)
    
    with zipfile.ZipFile(epub_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Process HTML files
    text_dir = os.path.join(temp_dir, 'text')
    files_fixed = 0
    
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Fix the content
                fixed_content = fix_html_content(content)
                
                # Write back if changed
                if fixed_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    files_fixed += 1
    
    print(f"Fixed {files_fixed} HTML files")
    
    # Repack EPUB
    print("Repacking EPUB...")
    if os.path.exists(epub_file):
        os.remove(epub_file)
    
    with zipfile.ZipFile(epub_file, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, temp_dir)
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)
    
    # Run epubcheck
    print("Running epubcheck...")
    try:
        result = subprocess.run(['java', '-jar', 'epubcheck.jar', epub_file], 
                              capture_output=True, text=True)
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)
        print("Epubcheck completed. Results saved to output.txt")
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == '__main__':
    main()