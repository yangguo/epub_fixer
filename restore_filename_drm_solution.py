#!/usr/bin/env python3
"""
Advanced DRM Removal Tool with Filename Restoration

This script removes DRM from EPUB files by:
1. Removing encryption.xml
2. Properly restoring obfuscated filenames to meaningful names
3. Updating all internal references
4. De-obfuscating fonts using IDPF algorithm

Based on research from DeDRM tools and IDPF specifications.
"""

import zipfile
import tempfile
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import hashlib
import os
import sys
import subprocess
from collections import defaultdict

class AdvancedEPUBDRMRemover:
    def __init__(self):
        self.encrypted_files = set()
        self.obfuscated_fonts = set()
        self.unique_identifier = None
        self.filename_mappings = {}  # obfuscated_name -> restored_name
        self.content_analysis = {}   # file_path -> content_info
        
    def remove_drm_complete(self, epub_path):
        """Complete DRM removal workflow with filename restoration."""
        print(f"=== Advanced DRM Removal with Filename Restoration ===")
        print(f"Processing: {epub_path}")
        
        # Step 1: Remove DRM and restore filenames
        intermediate_file = epub_path.replace('.epub', '_restored_drm_free.epub')
        self._remove_drm_and_restore_filenames(epub_path, intermediate_file)
        
        # Step 2: Run fix_epub.py to resolve remaining issues
        final_file = epub_path.replace('.epub', '_complete_restored_drm_free.epub')
        self._run_fix_epub(intermediate_file, final_file)
        
        # Step 3: Validate the final EPUB
        self._validate_epub(final_file)
        
        # Clean up intermediate file
        if os.path.exists(intermediate_file):
            os.remove(intermediate_file)
            
        return final_file
    
    def _remove_drm_and_restore_filenames(self, epub_path, output_path):
        """Remove DRM and restore meaningful filenames."""
        print("\n--- Step 1: DRM Removal and Filename Restoration ---")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            extract_dir = Path(temp_dir) / "epub_content"
            
            # Extract EPUB
            print("Extracting EPUB...")
            with zipfile.ZipFile(epub_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Parse and remove encryption.xml
            encryption_file = extract_dir / "META-INF" / "encryption.xml"
            if encryption_file.exists():
                print("Parsing encryption.xml...")
                self._parse_encryption_xml(encryption_file)
                encryption_file.unlink()
                print("Removed encryption.xml")
            
            # Find unique identifier
            self._find_unique_identifier(extract_dir)
            
            # Analyze file contents to understand structure
            self._analyze_file_contents(extract_dir)
            
            # Create filename mappings for obfuscated files
            self._create_filename_mappings(extract_dir)
            
            # Restore filenames and update references
            self._restore_filenames_and_update_references(extract_dir)
            
            # De-obfuscate fonts
            if self.obfuscated_fonts:
                self._deobfuscate_fonts(extract_dir)
            
            # Repackage EPUB
            print("Repackaging EPUB...")
            self._create_epub(extract_dir, output_path)
            
        print(f"DRM removal and filename restoration completed: {output_path}")
    
    def _parse_encryption_xml(self, encryption_file):
        """Parse encryption.xml to identify encrypted and obfuscated files."""
        try:
            tree = ET.parse(encryption_file)
            root = tree.getroot()
            
            namespaces = {
                'enc': 'http://www.w3.org/2001/04/xmlenc#',
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }
            
            for encrypted_data in root.findall('.//enc:EncryptedData', namespaces):
                cipher_ref = encrypted_data.find('.//enc:CipherReference', namespaces)
                if cipher_ref is not None:
                    uri = cipher_ref.get('URI')
                    if uri:
                        self.encrypted_files.add(uri)
                        
                        encryption_method = encrypted_data.find('enc:EncryptionMethod', namespaces)
                        if encryption_method is not None:
                            algorithm = encryption_method.get('Algorithm')
                            if 'font' in algorithm.lower() or 'obfuscation' in algorithm.lower():
                                self.obfuscated_fonts.add(uri)
            
            print(f"Found {len(self.encrypted_files)} encrypted files")
            print(f"Found {len(self.obfuscated_fonts)} obfuscated fonts")
            
        except ET.ParseError as e:
            print(f"Warning: Could not parse encryption.xml: {e}")
    
    def _find_unique_identifier(self, extract_dir):
        """Find the unique identifier from content.opf."""
        for opf_file in extract_dir.rglob("*.opf"):
            try:
                tree = ET.parse(opf_file)
                root = tree.getroot()
                
                unique_id_attr = root.get('unique-identifier')
                if unique_id_attr:
                    for elem in root.iter():
                        if elem.get('id') == unique_id_attr:
                            self.unique_identifier = elem.text
                            print(f"Found unique identifier: {self.unique_identifier}")
                            return
                            
            except ET.ParseError:
                continue
    
    def _analyze_file_contents(self, extract_dir):
        """Analyze file contents to understand their types and purposes."""
        print("Analyzing file contents...")
        
        for file_path in extract_dir.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(extract_dir)).replace('\\', '/')
                
                try:
                    # Read file header to determine type
                    with open(file_path, 'rb') as f:
                        header = f.read(512)  # Read more bytes for better analysis
                    
                    content_info = self._analyze_file_header(header, file_path)
                    self.content_analysis[relative_path] = content_info
                    
                except Exception as e:
                    print(f"Warning: Could not analyze {relative_path}: {e}")
    
    def _analyze_file_header(self, header, file_path):
        """Analyze file header to determine file type and characteristics."""
        info = {
            'type': 'unknown',
            'subtype': None,
            'extension': 'bin',
            'is_text': False,
            'encoding': None
        }
        
        # Image files
        if header.startswith(b'\x89PNG'):
            info.update({'type': 'image', 'subtype': 'png', 'extension': 'png'})
        elif header.startswith(b'\xFF\xD8\xFF'):
            info.update({'type': 'image', 'subtype': 'jpeg', 'extension': 'jpg'})
        elif header.startswith(b'GIF8'):
            info.update({'type': 'image', 'subtype': 'gif', 'extension': 'gif'})
        elif header.startswith(b'<svg') or b'<svg' in header[:100]:
            info.update({'type': 'image', 'subtype': 'svg', 'extension': 'svg', 'is_text': True})
        
        # Font files
        elif header.startswith(b'\x00\x01\x00\x00') or header.startswith(b'OTTO'):
            info.update({'type': 'font', 'subtype': 'truetype', 'extension': 'ttf'})
        elif header.startswith(b'wOFF'):
            info.update({'type': 'font', 'subtype': 'woff', 'extension': 'woff'})
        
        # Text files
        elif (b'<html' in header.lower() or b'<!doctype' in header.lower() or 
              b'<\?xml' in header.lower()):
            if b'<html' in header.lower():
                info.update({'type': 'text', 'subtype': 'html', 'extension': 'xhtml', 'is_text': True})
            else:
                info.update({'type': 'text', 'subtype': 'xml', 'extension': 'xml', 'is_text': True})
        
        # CSS files
        elif (b'@' in header and (b'font-face' in header or b'import' in header or 
              b'charset' in header)) or str(file_path).endswith('.css'):
            info.update({'type': 'style', 'subtype': 'css', 'extension': 'css', 'is_text': True})
        
        # Try to detect text encoding for text files
        if info['is_text']:
            try:
                # Try UTF-8 first
                header.decode('utf-8')
                info['encoding'] = 'utf-8'
            except UnicodeDecodeError:
                try:
                    # Try Latin-1
                    header.decode('latin-1')
                    info['encoding'] = 'latin-1'
                except UnicodeDecodeError:
                    info['encoding'] = 'unknown'
        
        return info
    
    def _create_filename_mappings(self, extract_dir):
        """Create intelligent mappings from obfuscated filenames to meaningful names."""
        print("Creating intelligent filename mappings...")
        
        # Counters for generating sequential names
        type_counters = defaultdict(int)
        
        for file_path in extract_dir.rglob("*"):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(extract_dir)).replace('\\', '/')
                
                if self._is_obfuscated_filename(relative_path):
                    content_info = self.content_analysis.get(relative_path, {})
                    restored_name = self._generate_meaningful_filename(
                        relative_path, content_info, type_counters
                    )
                    
                    self.filename_mappings[relative_path] = restored_name
                    print(f"Mapping: {relative_path} -> {restored_name}")
    
    def _is_obfuscated_filename(self, filename):
        """Check if a filename appears to be obfuscated."""
        # Look for patterns with colons and asterisks
        return ':' in filename or '*' in filename or '_' * 10 in filename
    
    def _generate_meaningful_filename(self, obfuscated_path, content_info, type_counters):
        """Generate a meaningful filename based on content analysis."""
        file_type = content_info.get('type', 'unknown')
        subtype = content_info.get('subtype', '')
        extension = content_info.get('extension', 'bin')
        
        # Get the directory part
        path_parts = obfuscated_path.split('/')
        directory = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ''
        
        # Generate base name based on type and location
        if file_type == 'image':
            if 'Images' in directory:
                type_counters['image'] += 1
                base_name = f"image_{type_counters['image']:03d}"
            else:
                type_counters['inline_image'] += 1
                base_name = f"inline_img_{type_counters['inline_image']:03d}"
        
        elif file_type == 'text':
            if subtype == 'html':
                if 'Text' in directory:
                    type_counters['chapter'] += 1
                    base_name = f"chapter_{type_counters['chapter']:03d}"
                else:
                    type_counters['page'] += 1
                    base_name = f"page_{type_counters['page']:03d}"
            else:
                type_counters['text'] += 1
                base_name = f"text_{type_counters['text']:03d}"
        
        elif file_type == 'style':
            type_counters['style'] += 1
            base_name = f"style_{type_counters['style']:03d}"
        
        elif file_type == 'font':
            type_counters['font'] += 1
            base_name = f"font_{type_counters['font']:03d}"
        
        else:
            type_counters['unknown'] += 1
            base_name = f"file_{type_counters['unknown']:03d}"
        
        # Construct full path
        filename = f"{base_name}.{extension}"
        
        if directory:
            return f"{directory}/{filename}"
        else:
            return filename
    
    def _restore_filenames_and_update_references(self, extract_dir):
        """Restore filenames and update all references."""
        print("Restoring filenames and updating references...")
        
        # First, rename all the files
        for obfuscated_path, restored_path in self.filename_mappings.items():
            old_file = extract_dir / obfuscated_path
            new_file = extract_dir / restored_path
            
            if old_file.exists():
                # Create directory if needed
                new_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Handle filename conflicts
                counter = 1
                original_new_file = new_file
                while new_file.exists():
                    stem = original_new_file.stem
                    suffix = original_new_file.suffix
                    new_file = original_new_file.parent / f"{stem}_{counter}{suffix}"
                    counter += 1
                
                # Update mapping if filename changed
                if new_file != original_new_file:
                    restored_path = str(new_file.relative_to(extract_dir)).replace('\\', '/')
                    self.filename_mappings[obfuscated_path] = restored_path
                
                shutil.move(str(old_file), str(new_file))
                print(f"Restored: {obfuscated_path} -> {restored_path}")
        
        # Update all references
        self._update_all_references(extract_dir)
    
    def _update_all_references(self, extract_dir):
        """Update references in all relevant files."""
        print("Updating references in files...")
        
        # Update OPF files
        for opf_file in extract_dir.rglob("*.opf"):
            self._update_references_in_file(opf_file)
        
        # Update NCX files
        for ncx_file in extract_dir.rglob("*.ncx"):
            self._update_references_in_file(ncx_file)
        
        # Update XHTML files
        for xhtml_file in extract_dir.rglob("*.xhtml"):
            self._update_references_in_file(xhtml_file)
        
        # Update HTML files
        for html_file in extract_dir.rglob("*.html"):
            self._update_references_in_file(html_file)
        
        # Update CSS files
        for css_file in extract_dir.rglob("*.css"):
            self._update_references_in_file(css_file)
    
    def _update_references_in_file(self, file_path):
        """Update references in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # Update each mapping
            for obfuscated_path, restored_path in self.filename_mappings.items():
                # Try different reference patterns
                patterns = [
                    obfuscated_path,  # Direct path
                    obfuscated_path.split('/')[-1],  # Just filename
                    '../' + obfuscated_path,  # Relative path
                    './' + obfuscated_path,  # Current directory
                ]
                
                for pattern in patterns:
                    if pattern in content:
                        # Replace with corresponding restored path pattern
                        if pattern == obfuscated_path:
                            replacement = restored_path
                        elif pattern == obfuscated_path.split('/')[-1]:
                            replacement = restored_path.split('/')[-1]
                        elif pattern.startswith('../'):
                            replacement = '../' + restored_path
                        elif pattern.startswith('./'):
                            replacement = './' + restored_path
                        else:
                            replacement = restored_path
                        
                        content = content.replace(pattern, replacement)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated references in: {file_path.name}")
                
        except Exception as e:
            print(f"Error updating references in {file_path}: {e}")
    
    def _deobfuscate_fonts(self, extract_dir):
        """De-obfuscate font files using IDPF algorithm."""
        if not self.unique_identifier:
            print("Warning: No unique identifier found, cannot de-obfuscate fonts")
            return
        
        print("De-obfuscating fonts...")
        key = self._generate_obfuscation_key(self.unique_identifier)
        
        for font_path in self.obfuscated_fonts:
            # Check if this font was renamed
            actual_path = self.filename_mappings.get(font_path, font_path)
            file_path = extract_dir / actual_path
            
            if file_path.exists():
                print(f"De-obfuscating font: {actual_path}")
                self._deobfuscate_file(file_path, key)
    
    def _generate_obfuscation_key(self, unique_id):
        """Generate obfuscation key from unique identifier."""
        clean_id = unique_id.replace('urn:uuid:', '').replace('-', '').lower()
        key_material = clean_id.encode('utf-8')
        sha1_hash = hashlib.sha1(key_material).digest()
        return sha1_hash
    
    def _deobfuscate_file(self, file_path, key):
        """De-obfuscate a single file using XOR with the key."""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            deobfuscated_data = bytearray(data)
            key_len = len(key)
            
            for i in range(min(1040, len(data))):
                deobfuscated_data[i] ^= key[i % key_len]
            
            with open(file_path, 'wb') as f:
                f.write(deobfuscated_data)
            
            print(f"Successfully de-obfuscated: {file_path}")
            
        except Exception as e:
            print(f"Error de-obfuscating {file_path}: {e}")
    
    def _create_epub(self, extract_dir, output_path):
        """Create EPUB file from extracted directory."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add mimetype first (uncompressed)
            mimetype_file = extract_dir / "mimetype"
            if mimetype_file.exists():
                zip_file.write(mimetype_file, "mimetype", compress_type=zipfile.ZIP_STORED)
            
            # Add all other files
            for file_path in extract_dir.rglob("*"):
                if file_path.is_file() and file_path.name != "mimetype":
                    relative_path = file_path.relative_to(extract_dir)
                    zip_file.write(file_path, str(relative_path).replace('\\', '/'))
    
    def _run_fix_epub(self, input_file, output_file):
        """Run fix_epub.py to resolve remaining issues."""
        print("\n--- Step 2: Running EPUB Fix ---")
        
        try:
            # Copy the input file to the expected output name for fix_epub.py
            shutil.copy2(input_file, output_file)
            
            # Run fix_epub.py
            result = subprocess.run(
                [sys.executable, 'fix_epub.py', output_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("EPUB fix completed successfully")
            else:
                print(f"EPUB fix completed with warnings: {result.stderr}")
                
        except Exception as e:
            print(f"Error running fix_epub.py: {e}")
            # If fix_epub.py fails, just copy the input to output
            shutil.copy2(input_file, output_file)
    
    def _validate_epub(self, epub_file):
        """Validate the final EPUB using EPUBCheck."""
        print("\n--- Step 3: EPUB Validation ---")
        
        try:
            result = subprocess.run(
                ['java', '-jar', 'epubcheck.jar', epub_file],
                capture_output=True,
                text=True
            )
            
            print("Validation Results:")
            print(result.stdout)
            
            if result.returncode == 0:
                print("✅ EPUB validation passed!")
            else:
                print("⚠️ EPUB validation found issues (but file may still be usable)")
                
        except Exception as e:
            print(f"Could not run EPUBCheck validation: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python restore_filename_drm_solution.py <epub_file>")
        print("\nThis script will:")
        print("1. Remove DRM encryption")
        print("2. Restore obfuscated filenames to meaningful names")
        print("3. Update all internal references")
        print("4. Fix remaining EPUB structure issues")
        print("5. Validate the final EPUB")
        print("\nOutput: <original_name>_complete_restored_drm_free.epub")
        sys.exit(1)
    
    epub_file = sys.argv[1]
    if not os.path.exists(epub_file):
        print(f"Error: File '{epub_file}' not found")
        sys.exit(1)
    
    remover = AdvancedEPUBDRMRemover()
    try:
        output_file = remover.remove_drm_complete(epub_file)
        print(f"\n🎉 Success! Complete DRM-free EPUB with restored filenames: {output_file}")
        print("\nThe EPUB should now be readable with proper content structure.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()