#!/usr/bin/env python3
import zipfile
import os

def extract_epub():
    epub_file = 'climate1.epub'
    extract_dir = 'climate1_extracted'
    
    if os.path.exists(extract_dir):
        import shutil
        shutil.rmtree(extract_dir)
    
    with zipfile.ZipFile(epub_file, 'r') as z:
        z.extractall(extract_dir)
    
    print(f'EPUB extracted to {extract_dir}')

if __name__ == '__main__':
    extract_epub()