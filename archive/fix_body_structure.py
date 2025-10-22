#!/usr/bin/env python3
import zipfile
import os
import re
import shutil
import subprocess
from pathlib import Path

def fix_body_structure(content):
    """
    Fix malformed body tags and ensure proper HTML structure
    """
    # First, fix malformed body tag attributes
    # Pattern: <body> id="..." class="..." class="..." class="..."
    body_pattern = r'<body>([^>]*?)>'
    
    def fix_body_tag(match):
        attributes = match.group(1).strip()
        if not attributes:
            return '<body>'
        
        # Extract all attributes and combine duplicate classes
        id_attrs = re.findall(r'id="([^"]*?)"', attributes)
        class_attrs = re.findall(r'class="([^"]*?)"', attributes)
        other_attrs = re.findall(r'(\w+)="([^"]*?)"', attributes)
        
        # Filter out id and class from other_attrs to avoid duplicates
        other_attrs = [(k, v) for k, v in other_attrs if k not in ['id', 'class']]
        
        # Build proper body tag
        body_parts = ['<body']
        
        if id_attrs:
            body_parts.append(f' id="{id_attrs[0]}"')
        
        if class_attrs:
            combined_classes = ' '.join(class_attrs)
            body_parts.append(f' class="{combined_classes}"')
        
        for attr_name, attr_value in other_attrs:
            body_parts.append(f' {attr_name}="{attr_value}"')
        
        body_parts.append('>')
        return ''.join(body_parts)
    
    content = re.sub(body_pattern, fix_body_tag, content)
    
    # Fix content that appears directly after body tag without proper containers
    # Look for pattern: <body...> class="..." or <body...> id="..." or <body...> text
    body_content_pattern = r'(<body[^>]*>)\s*((?:class="[^"]*"|id="[^"]*"|[^<]+)*)(.*?)(?=</body>|$)'
    
    def fix_body_content(match):
        body_tag = match.group(1)
        loose_content = match.group(2).strip() if match.group(2) else ''
        rest_content = match.group(3) if match.group(3) else ''
        
        # If there's loose content after body tag, wrap it in a div
        if loose_content:
            # Extract any class or id attributes from loose content
            loose_classes = re.findall(r'class="([^"]*?)"', loose_content)
            loose_ids = re.findall(r'id="([^"]*?)"', loose_content)
            
            # Remove these attributes from loose content
            loose_content = re.sub(r'\s*(?:class|id)="[^"]*?"', '', loose_content)
            loose_content = loose_content.strip()
            
            # Create a wrapper div
            div_parts = ['<div']
            if loose_classes:
                div_parts.append(f' class="{" ".join(loose_classes)}"')
            if loose_ids:
                div_parts.append(f' id="{loose_ids[0]}"')
            div_parts.append('>')
            
            # Add any remaining text content
            if loose_content and not loose_content.startswith('<'):
                div_parts.append(loose_content)
            
            return body_tag + ''.join(div_parts) + rest_content + '</div>'
        
        return body_tag + rest_content
    
    content = re.sub(body_content_pattern, fix_body_content, content, flags=re.DOTALL)
    
    # Ensure proper closing tags
    if '</body>' not in content:
        content = content.rstrip() + '\n</body>\n</html>'
    
    if '</html>' not in content:
        content = content.rstrip() + '\n</html>'
    
    return content

def process_epub(epub_path):
    """
    Process EPUB file to fix body structure issues
    """
    # Create backup
    backup_path = epub_path.replace('.epub', '_backup.epub')
    shutil.copy2(epub_path, backup_path)
    print(f"Created backup: {backup_path}")
    
    # Extract EPUB
    extract_dir = 'temp_epub_extract'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # Process HTML files
    text_dir = os.path.join(extract_dir, 'text')
    files_processed = 0
    
    if os.path.exists(text_dir):
        for filename in os.listdir(text_dir):
            if filename.endswith('.html'):
                file_path = os.path.join(text_dir, filename)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    fixed_content = fix_body_structure(content)
                    
                    if fixed_content != original_content:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(fixed_content)
                        files_processed += 1
                        print(f"Fixed body structure in: {filename}")
                        
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
    
    print(f"\nProcessed {files_processed} files")
    
    # Repack EPUB
    print("Repacking EPUB...")
    
    # Remove old EPUB
    os.remove(epub_path)
    
    # Create new EPUB
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, extract_dir)
                # Ensure forward slashes in zip file paths
                arc_name = arc_name.replace('\\', '/')
                zip_ref.write(file_path, arc_name)
    
    # Clean up
    shutil.rmtree(extract_dir)
    
    print("EPUB repacked successfully")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
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
        
        print("Epubcheck completed. Results saved to output.txt")
        
    except Exception as e:
        print(f"Error running epubcheck: {e}")

if __name__ == "__main__":
    epub_file = "future1.epub"
    if os.path.exists(epub_file):
        process_epub(epub_file)
    else:
        print(f"EPUB file '{epub_file}' not found")