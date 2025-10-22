#!/usr/bin/env python3
import zipfile
import os
import re
import subprocess
from pathlib import Path

def extract_epub(epub_path, extract_dir):
    """Extract EPUB file to directory"""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    print(f"Extracted {epub_path} to {extract_dir}")

def fix_html_structure(content):
    """Fix malformed HTML structure"""
    # Remove extra > characters
    content = re.sub(r'>+', '>', content)
    
    # Extract title if it exists
    title_match = re.search(r'<title>([^<]*)</title>', content)
    title = title_match.group(1) if title_match else 'Document'
    
    # Extract all meta and link tags from anywhere in the document
    meta_tags = re.findall(r'<meta[^>]*/?>', content)
    link_tags = re.findall(r'<link[^>]*/?>', content)
    
    # Remove meta and link tags from their current positions
    content = re.sub(r'<meta[^>]*/?>', '', content)
    content = re.sub(r'<link[^>]*/?>', '', content)
    
    # Remove the existing title tag from body if it exists there
    content = re.sub(r'<title>[^<]*</title>', '', content)
    
    # Clean up any remaining malformed head structure
    content = re.sub(r'<head>.*?</head>', '', content, flags=re.DOTALL)
    
    # Build proper head section
    head_content = ['<head>', f'<title>{title}</title>']
    
    # Add meta tags to head
    for meta_tag in meta_tags:
        # Fix common meta tag issues
        meta_tag = re.sub(r'\s+/>', ' />', meta_tag)
        if 'charset=' in meta_tag and not meta_tag.endswith(' />'):
            meta_tag = meta_tag.rstrip('>') + ' />'
        head_content.append(meta_tag)
    
    # Add link tags to head
    for link_tag in link_tags:
        # Fix common link tag issues
        link_tag = re.sub(r'\s+/>', ' />', link_tag)
        if not link_tag.endswith(' />'):
            link_tag = link_tag.rstrip('>') + ' />'
        # Add type attribute if missing for CSS links
        if 'rel="stylesheet"' in link_tag and 'type=' not in link_tag:
            link_tag = link_tag.replace(' />', ' type="text/css" />')
        head_content.append(link_tag)
    
    head_content.append('</head>')
    head_section = '\n'.join(head_content)
    
    # Insert the proper head section after the html opening tag
    content = re.sub(r'(<html[^>]*>)', r'\1\n' + head_section + '\n<body>', content)
    
    # Clean up any remaining issues
    content = re.sub(r'<body>\s*<body>', '<body>', content)
    content = re.sub(r'</body>\s*</body>', '</body>', content)
    
    # Ensure proper closing tags
    if '</body>' not in content:
        content = content.rstrip() + '\n</body>'
    if '</html>' not in content:
        content = content.rstrip() + '\n</html>'
    
    # Clean up extra whitespace and newlines
    content = re.sub(r'\n\s*\n', '\n', content)
    
    return content

def process_html_files(extract_dir):
    """Process all HTML files in the extracted EPUB"""
    text_dir = os.path.join(extract_dir, 'text')
    if not os.path.exists(text_dir):
        print("No text directory found")
        return 0
    
    files_processed = 0
    for filename in os.listdir(text_dir):
        if filename.endswith('.html'):
            file_path = os.path.join(text_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            content = fix_html_structure(content)
            
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_processed += 1
                print(f"Fixed HTML structure in {filename}")
    
    return files_processed

def repack_epub(extract_dir, epub_path):
    """Repack the EPUB file"""
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, extract_dir)
                zip_ref.write(file_path, arc_name)
    print(f"Repacked EPUB as {epub_path}")

def run_epubcheck(epub_path):
    """Run epubcheck on the EPUB file"""
    try:
        result = subprocess.run(
            ['java', '-jar', 'epubcheck.jar', epub_path],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        # Write output to file
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(result.stdout)
            if result.stderr:
                f.write('\n--- STDERR ---\n')
                f.write(result.stderr)
        
        print(f"EPUBCheck completed. Output written to output.txt")
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")
        return False

def main():
    epub_file = 'future1.epub'
    extract_dir = 'temp_extract'
    backup_file = 'future1_backup.epub'
    
    # Create backup
    if os.path.exists(epub_file):
        import shutil
        shutil.copy2(epub_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Clean up previous extraction
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    try:
        # Extract EPUB
        extract_epub(epub_file, extract_dir)
        
        # Process HTML files
        files_processed = process_html_files(extract_dir)
        print(f"Processed {files_processed} HTML files")
        
        # Repack EPUB
        repack_epub(extract_dir, epub_file)
        
        # Run epubcheck
        print("Running epubcheck...")
        run_epubcheck(epub_file)
        
    finally:
        # Clean up
        if os.path.exists(extract_dir):
            import shutil
            shutil.rmtree(extract_dir)

if __name__ == '__main__':
    main()