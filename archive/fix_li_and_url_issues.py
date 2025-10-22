import zipfile
import re
import os

def fix_li_and_url_issues():
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
                
                # Fix 1: Remove malformed '>' characters from URLs
                content = re.sub(r'href=">([^"]+)"', r'href="\1"', content)
                content = re.sub(r'src=">([^"]+)"', r'src="\1"', content)
                
                # Fix 2: Fix malformed class attributes with '>' 
                content = re.sub(r'class=">([^"]+)"', r'class="\1"', content)
                
                # Fix 3: Wrap orphaned <li> elements in <ul>
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    # Check if line contains <li> but no <ul> or <ol>
                    if '<li' in line and '<ul' not in line and '<ol' not in line:
                        # Count <li> tags in this line
                        li_count = line.count('<li')
                        if li_count > 0:
                            # Wrap the entire line content in <ul>
                            # First, find where the actual content starts after opening tags
                            body_match = re.search(r'(<body[^>]*>.*?<div[^>]*>)', line)
                            if body_match:
                                prefix = body_match.group(1)
                                rest = line[len(prefix):]
                                # Insert <ul> after the opening div
                                lines[i] = prefix + '<ul>' + rest + '</ul>'
                            else:
                                # Simple case: just wrap the line
                                lines[i] = '<ul>' + line + '</ul>'
                
                content = '\n'.join(lines)
                
                # Fix 4: Fix malformed div attributes
                content = re.sub(r'>div class="', r'<div class="', content)
                
                # Fix 5: Fix missing closing brackets in opening tags
                content = re.sub(r'class="([^"]+)"\s+id="([^"]+)"\s+([^>]+)"\s*id="([^"]+)"', 
                                r'class="\1" id="\2"', content)
                
                # Fix 6: Clean up malformed attribute sequences
                content = re.sub(r'"\s+class="', r'" class="', content)
                content = re.sub(r'"\s+id="', r'" id="', content)
                
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
    fix_li_and_url_issues()