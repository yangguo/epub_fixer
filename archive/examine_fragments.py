#!/usr/bin/env python3
import zipfile

def examine_fragment_errors():
    """Examine fragment identifier errors in the EPUB"""
    epub_path = "future1.epub"
    
    with zipfile.ZipFile(epub_path, 'r') as z:
        # Check part0000_split_003.html around line 198
        content = z.read('text/part0000_split_003.html').decode('utf-8')
        lines = content.split('\n')
        
        print("Examining part0000_split_003.html:")
        for i in range(195, min(202, len(lines))):
            line_num = i + 1
            line = lines[i]
            print(f"Line {line_num}: {line}")
            
            # Look for href attributes with fragment identifiers
            if 'href="#' in line:
                import re
                hrefs = re.findall(r'href="#([^"]+)"', line)
                for href in hrefs:
                    print(f"  -> Fragment ID found: #{href}")
        
        print("\n" + "="*50 + "\n")
        
        # Check another file with fragment errors
        content2 = z.read('text/part0006_split_004.html').decode('utf-8')
        lines2 = content2.split('\n')
        
        print("Examining part0006_split_004.html:")
        for i in range(38, min(46, len(lines2))):
            line_num = i + 1
            line = lines2[i]
            print(f"Line {line_num}: {line}")
            
            # Look for href attributes with fragment identifiers
            if 'href="#' in line:
                import re
                hrefs = re.findall(r'href="#([^"]+)"', line)
                for href in hrefs:
                    print(f"  -> Fragment ID found: #{href}")

if __name__ == "__main__":
    examine_fragment_errors()