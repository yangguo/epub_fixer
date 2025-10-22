#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
import subprocess
from pathlib import Path

def fix_remaining_issues(content):
    """
    Fix remaining issues: missing closing div tags and malformed attributes
    """
    # Fix malformed attributes that are missing equals sign
    # Pattern: attribute_name"> or attribute_name">
    malformed_attr_patterns = [
        (r'\s+(iii|acknowledgment|eula)">', r' class="\1">'),
        (r'\s+(iii|acknowledgment|eula)\s*>', r' class="\1">'),
        (r'<h1([^>]*?)\s+(iii|acknowledgment|eula)([^>]*?)>', r'<h1\1 class="\2"\3>'),
    ]
    
    for pattern, replacement in malformed_attr_patterns:
        content = re.sub(pattern, replacement, content)
    
    # Ensure all div tags are properly closed
    # Count opening and closing div tags
    opening_divs = len(re.findall(r'<div[^>]*>', content))
    closing_divs = len(re.findall(r'</div>', content))
    
    # If we have more opening divs than closing divs, add missing closing tags
    missing_divs = opening_divs - closing_divs
    
    if missing_divs > 0:
        # Add missing closing div tags before </body>
        if '</body>' in content:
            div_closings = '</div>' * missing_divs
            content = content.replace('</body>', f'{div_closings}\n</body>')
        else:
            # If no </body> tag, add at the end
            div_closings = '</div>' * missing_divs
            content = content.rstrip() + div_closings + '\n</body>\n</html>'
    
    # Fix titlepage.xhtml specific issues
    if 'titlepage' in content or content.startswith('<?xml'):
        # Fix text appearing before head tag
        content = re.sub(r'(<html[^>]*>)([^<]*?)(<head>)', r'\1\n\3', content)
        
        # Ensure proper html closing
        if '</html>' not in content:
            content = content.rstrip() + '\n</html>'
    
    return content

def fix_mimetype_issue(epub_path):
    """
    Fix the mimetype file ordering issue
    """
    # Extract EPUB
    extract_dir = 'temp_epub_extract_final'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Remove old EPUB
    os.remove(epub_path)
    
    # Create new EPUB with mimetype first
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_STORED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype')
        
        # Add all other files (compressed)
        with zipfile.ZipFile(epub_path, 'a', zipfile.ZIP_DEFLATED) as zip_ref_compressed:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == 'mimetype':
                        continue  # Already added
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, extract_dir)
                    # Ensure forward slashes in zip file paths
                    arc_name = arc_name.replace('\\', '/')
                    zip_ref_compressed.write(file_path, arc_name)
    
    # Clean up
    shutil.rmtree(extract_dir)

def process_epub(epub_path):
    """
    Process EPUB file to fix remaining issues
    """
    # Create backup
    backup_path = epub_path.replace('.epub', '_final_backup.epub')
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = 'temp_epub_extract_final'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process HTML files
    files_processed = 0
    
    # Process files in text directory
    text_dir = os.path.join(extract_dir, 'text')
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    fixed_content = fix_remaining_issues(content)
                    
                    if fixed_content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        files_processed += 1
                        print(f"Fixed remaining issues in: {filename}")
                        
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
    
    # Process titlepage.xhtml
    titlepage_path = os.path.join(extract_dir, 'titlepage.xhtml')
    if os.path.exists(titlepage_path):
        try:
            with open(titlepage_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixed_content = fix_remaining_issues(content)
            
            if fixed_content != original_content:
                with open(titlepage_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                files_processed += 1
                print(f"Fixed titlepage.xhtml")
                
        except Exception as e:
            print(f"Error processing titlepage.xhtml: {e}")
    
    print(f"\nProcessed {files_processed} files")
    
    # Repack EPUB with proper mimetype ordering
    print("Repacking EPUB with proper mimetype ordering...")
    
    # Remove old EPUB
    os.remove(epub_path)
    
    # Create new EPUB with mimetype first
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_STORED) as zip_ref:
        # Add mimetype first (uncompressed)
        mimetype_path = os.path.join(extract_dir, 'mimetype')
        if os.path.exists(mimetype_path):
            zip_ref.write(mimetype_path, 'mimetype')
    
    # Add all other files (compressed)
    with zipfile.ZipFile(epub_path, 'a', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == 'mimetype':
                    continue  # Already added
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, extract_dir)
                # Ensure forward slashes in zip file paths
                arc_name = arc_name.replace('\\', '/')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    print("EPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning final epubcheck...")
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
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)
        
        print("Final epubcheck completed. Results saved to output.txt")
        
        # Print summary
        if 'Check finished with errors' in result.stdout:
            print("\n⚠️  EPUB still has some validation errors.")
        elif 'No errors or warnings detected' in result.stdout:
            print("\n✅ EPUB validation successful! No errors detected.")
        else:
            print("\n📋 EPUB validation completed. Check output.txt for details.")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    epub_file = "future1.epub"
    if os.path.exists(epub_file):
        process_epub(epub_file)
    else:
        print(f"EPUB file '{epub_file}' not found")