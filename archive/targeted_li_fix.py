import zipfile
import re
import os

def targeted_li_fix():
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
                
                # Fix the specific problematic structure in line 9
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '<li' in line and len(line) > 1000:  # Target the problematic long lines
                        # Remove the incorrectly placed <ul> and </ul> from my previous fix
                        if line.startswith('<body><div class="calibre"><ul>'):
                            line = line.replace('<body><div class="calibre"><ul>', '<body><div class="calibre">')
                        if line.endswith('</body></ul>\r'):
                            line = line.replace('</body></ul>\r', '</body>\r')
                        
                        # Fix malformed attributes and missing closing brackets
                        # Fix: class="toclist" id="toc____h1_class_"<div
                        line = re.sub(r'class="([^"]+)"\s+id="([^"]+)"<div', r'class="\1" id="\2"><div', line)
                        
                        # Fix missing closing brackets in href attributes
                        line = re.sub(r'href="([^"]+)"<div', r'href="\1"><div', line)
                        
                        # Fix missing closing brackets in other attributes
                        line = re.sub(r'class="([^"]+)"<', r'class="\1"><', line)
                        
                        # Now properly wrap the list items in <ul>
                        # Find the section with <li> elements and wrap only that part
                        if '<li' in line:
                            # Split the line into parts: before li, li section, after li
                            # Find where the first <li> starts
                            li_start = line.find('<li')
                            # Find where the last </li> ends
                            li_end = line.rfind('</li>') + 5
                            
                            if li_start != -1 and li_end > li_start:
                                before_li = line[:li_start]
                                li_section = line[li_start:li_end]
                                after_li = line[li_end:]
                                
                                # Wrap only the li section in ul tags
                                line = before_li + '<ul>' + li_section + '</ul>' + after_li
                        
                        lines[i] = line
                
                content = '\n'.join(lines)
                
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
    targeted_li_fix()