import zipfile
import re
import os

def comprehensive_structure_rebuild():
    # Extract EPUB
    with zipfile.ZipFile('future1.epub', 'r') as epub:
        epub.extractall('temp_epub')
    
    files_fixed = 0
    
    # Process all HTML files
    for root, dirs, files in os.walk('temp_epub'):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                lines = content.split('\n')
                
                # Fix the fundamental structure issues
                for i, line in enumerate(lines):
                    # Remove misplaced <ul> tags from head section (lines 6-7)
                    if i in [5, 6]:  # Lines 6 and 7 (0-indexed: 5, 6)
                        if '<ul>' in line and '<link' in line:
                            # Remove the <ul> and </ul> tags, keep the link
                            line = re.sub(r'<ul>\s*', '', line)
                            line = re.sub(r'\s*</ul>', '', line)
                            lines[i] = line
                    
                    # Fix the massive malformed line 9
                    elif i == 8:  # Line 9 (0-indexed: 8)
                        if len(line) > 1000:  # This is the problematic line
                            # Start fresh with a proper structure
                            # Extract the basic components we need
                            
                            # Remove any existing <ul> wrapper that was incorrectly added
                            if line.startswith('<body><div class="calibre"><ul>'):
                                line = line.replace('<body><div class="calibre"><ul>', '<body><div class="calibre">')
                            if line.endswith('</ul>'):
                                line = line.rstrip('</ul>')
                            
                            # Fix basic structure issues
                            # 1. Fix missing closing brackets
                            line = re.sub(r'class="([^"]+)"\s+id="([^"]+)"([^>]*?)(<[^>]+>)', r'class="\1" id="\2">\4', line)
                            
                            # 2. Fix href attributes missing closing brackets
                            line = re.sub(r'href="([^"]+)"(<[^>]+>)', r'href="\1">\2', line)
                            
                            # 3. Fix malformed div tags
                            line = re.sub(r'"<div', r'"><div', line)
                            
                            # 4. Fix duplicate attributes
                            line = re.sub(r'class="([^"]+)"\s+class="([^"]+)"', r'class="\1 \2"', line)
                            line = re.sub(r'id="([^"]+)"\s+id="([^"]+)"', r'id="\1"', line)
                            
                            # 5. Fix malformed attribute names
                            line = re.sub(r'\s+([a-zA-Z0-9_-]+)"\s*id="', r' id="', line)
                            
                            # 6. Ensure proper tag closure
                            line = re.sub(r'<(\w+)([^>]*?)([^>])\s*<', r'<\1\2\3><', line)
                            
                            # 7. Fix body tag closure issue
                            if '</body>' in line and not line.endswith('</body>'):
                                # Move </body> to the end
                                line = line.replace('</body>', '') + '</body>'
                            
                            lines[i] = line
                
                content = '\n'.join(lines)
                
                # Additional global fixes
                # Fix any remaining malformed tags
                content = re.sub(r'<(\w+)([^>]*?)([a-zA-Z0-9_-]+)"\s*>', r'<\1\2>', content)
                
                # Fix unclosed tags that should be self-closing or properly closed
                content = re.sub(r'<(img|br|hr|meta|link)([^>]*?)([^/])>', r'<\1\2\3 />', content)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_fixed += 1
                    print(f"Fixed: {file}")
    
    print(f"\nTotal files fixed: {files_fixed}")
    
    # Repack EPUB
    print("\nRepacking EPUB...")
    with zipfile.ZipFile('future1.epub', 'w', zipfile.ZIP_DEFLATED) as epub:
        for root, dirs, files in os.walk('temp_epub'):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, 'temp_epub')
                epub.write(file_path, arc_path)
    
    # Clean up
    import shutil
    shutil.rmtree('temp_epub')
    
    print("EPUB repacked successfully!")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    os.system('java -jar epubcheck.jar future1.epub > output.txt 2>&1')
    print("Epubcheck completed. Results saved to output.txt")

if __name__ == "__main__":
    comprehensive_structure_rebuild()