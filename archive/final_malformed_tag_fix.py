import zipfile
import re
import os
import subprocess

def fix_malformed_tags(content):
    """Fix various malformed HTML tag patterns"""
    original_content = content
    
    # Fix malformed href attributes missing closing >
    # Pattern: href="..."<tag instead of href="...">content<tag
    content = re.sub(r'href="([^"]*?)"<(\w+)', r'href="\1">\2', content)
    
    # Fix malformed src attributes missing closing >
    content = re.sub(r'src="([^"]*?)"<(\w+)', r'src="\1">\2', content)
    
    # Fix malformed class attributes missing closing >
    content = re.sub(r'class="([^"]*?)"<(\w+)', r'class="\1">\2', content)
    
    # Fix malformed id attributes missing closing >
    content = re.sub(r'id="([^"]*?)"<(\w+)', r'id="\1">\2', content)
    
    # Fix tags that are missing closing > before other content
    # Pattern: <tag attr="value"text instead of <tag attr="value">text
    content = re.sub(r'<(\w+)([^>]*?)"([^>"]+?)(?=<|$)', r'<\1\2">\3', content)
    
    # Fix malformed opening tags that have extra characters
    # Pattern: <tag>< or <tag>>< 
    content = re.sub(r'<(\w+[^>]*)>>?<', r'<\1><', content)
    
    # Fix attribute names that are not properly quoted
    # Pattern: <h1 class="class">="clas">s="
    content = re.sub(r'<(h\d+)\s+class="[^"]*?">="[^"]*?">s="[^"]*?"', r'<\1 class="calibre1"', content)
    
    # Fix malformed h1 tags with orphaned attributes
    # Pattern: <h1 acknowledgment class=... should be <h1 class=...
    content = re.sub(r'<(h\d+)\s+\w+\s+(class="[^"]*?")', r'<\1 \2', content)
    
    # Fix malformed h1 tags with attribute name issues
    # Pattern: <h1 iii class=... should be <h1 class=...
    content = re.sub(r'<(h\d+)\s+\w{1,3}\s+(class="[^"]*?")', r'<\1 \2', content)
    
    # Fix malformed div tags missing closing >
    # Pattern: <div class="..." followed by content without >
    content = re.sub(r'<div\s+([^>]*?)"([^>"]+?)(?=<|\w)', r'<div \1">\2', content)
    
    # Fix malformed b tags missing closing >
    content = re.sub(r'<b\s+([^>]*?)"([^>"]+?)(?=<|\w)', r'<b \1">\2', content)
    
    # Fix malformed a tags missing closing >
    content = re.sub(r'<a\s+([^>]*?)"([^>"]+?)(?=<|\w)', r'<a \1">\2', content)
    
    # Balance div tags
    div_open = content.count('<div')
    div_close = content.count('</div>')
    if div_open > div_close:
        missing_closes = div_open - div_close
        # Add missing closing div tags before </body>
        if '</body>' in content:
            content = content.replace('</body>', '</div>' * missing_closes + '</body>')
        elif '</html>' in content:
            content = content.replace('</html>', '</div>' * missing_closes + '</html>')
    
    # Balance h1 tags
    h1_open = content.count('<h1')
    h1_close = content.count('</h1>')
    if h1_open > h1_close:
        missing_closes = h1_open - h1_close
        # Add missing closing h1 tags before </div> or </body>
        if '</div>' in content:
            content = content.replace('</div>', '</h1>' * missing_closes + '</div>', 1)
        elif '</body>' in content:
            content = content.replace('</body>', '</h1>' * missing_closes + '</body>')
    
    # Balance body tags
    body_open = content.count('<body')
    body_close = content.count('</body>')
    if body_open > body_close:
        missing_closes = body_open - body_close
        if '</html>' in content:
            content = content.replace('</html>', '</body>' * missing_closes + '</html>')
        else:
            content += '</body>' * missing_closes
    
    return content, content != original_content

def process_epub():
    # Create backup
    if not os.path.exists('future1_backup.epub'):
        import shutil
        shutil.copy2('future1.epub', 'future1_backup.epub')
        print("Created backup: future1_backup.epub")
    
    files_fixed = 0
    
    # Read the EPUB
    with zipfile.ZipFile('future1.epub', 'r') as epub_read:
        file_list = epub_read.namelist()
        
        # Create new EPUB
        with zipfile.ZipFile('future1_temp.epub', 'w', zipfile.ZIP_DEFLATED) as epub_write:
            # First, write mimetype without compression
            if 'mimetype' in file_list:
                epub_write.writestr('mimetype', epub_read.read('mimetype'), compress_type=zipfile.ZIP_STORED)
            
            # Process all files
            for file_path in file_list:
                if file_path == 'mimetype':
                    continue  # Already written
                    
                if file_path.endswith('.html') or file_path.endswith('.xhtml'):
                    try:
                        content = epub_read.read(file_path).decode('utf-8')
                        fixed_content, was_changed = fix_malformed_tags(content)
                        
                        if was_changed:
                            files_fixed += 1
                            print(f"Fixed malformed tags in: {file_path}")
                            
                        epub_write.writestr(file_path, fixed_content.encode('utf-8'))
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        epub_write.writestr(file_path, epub_read.read(file_path))
                else:
                    # Copy other files as-is
                    epub_write.writestr(file_path, epub_read.read(file_path))
    
    # Replace original with fixed version
    os.replace('future1_temp.epub', 'future1.epub')
    
    print(f"\nFixed malformed tags in {files_fixed} files")
    print("EPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    try:
        result = subprocess.run(['java', '-jar', 'epubcheck.jar', 'future1.epub'], 
                              capture_output=True, text=True, timeout=60)
        
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)
        
        print(f"Epubcheck completed with exit code: {result.returncode}")
        print("Results saved to output.txt")
        
    except subprocess.TimeoutExpired:
        print("Epubcheck timed out after 60 seconds")
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    process_epub()