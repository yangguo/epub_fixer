import zipfile
import os
import subprocess

def fix_titlepage():
    epub_path = 'future1.epub'
    temp_dir = 'temp_epub_fix'
    
    # Extract EPUB
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Fix titlepage.xhtml with proper XHTML structure
    titlepage_path = os.path.join(temp_dir, 'titlepage.xhtml')
    if os.path.exists(titlepage_path):
        # Create a proper XHTML titlepage
        proper_titlepage = '''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
    <meta name="calibre:cover" content="true"/>
    <title>Cover</title>
    <style type="text/css" title="override_css">
        @page {padding: 0pt; margin:0pt}
        body {text-align: center; padding:0pt; margin: 0pt;}
    </style>
</head>
<body>
    <div>
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
             version="1.1" width="100%" height="100%" viewBox="0 0 758 1186" 
             preserveAspectRatio="none">
            <image width="758" height="1186" xlink:href="images/00001.jpeg"/>
        </svg>
    </div>
</body>
</html>'''
        
        with open(titlepage_path, 'w', encoding='utf-8') as f:
            f.write(proper_titlepage)
        
        print("Fixed titlepage.xhtml with proper XHTML structure")
    
    # Create mimetype file first (must be first in archive)
    mimetype_path = os.path.join(temp_dir, 'mimetype')
    with open(mimetype_path, 'w', encoding='utf-8') as f:
        f.write('application/epub+zip')
    
    # Repack EPUB with mimetype first
    with zipfile.ZipFile(epub_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
        # Add mimetype first (uncompressed)
        zip_ref.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        # Add all other files
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file != 'mimetype':  # Skip mimetype as it's already added
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, arcname)
    
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)
    
    print("\nEPUB repacked successfully!")
    
    # Run epubcheck
    print("\nRunning epubcheck...")
    result = subprocess.run(['java', '-jar', 'epubcheck.jar', epub_path], 
                          capture_output=True, text=True)
    
    # Save output
    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write(result.stdout)
        if result.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
    
    print("Epubcheck completed. Results saved to output.txt")

if __name__ == "__main__":
    fix_titlepage()