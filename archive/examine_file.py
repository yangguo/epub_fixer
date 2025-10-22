#!/usr/bin/env python3
import zipfile

def examine_file():
    with zipfile.ZipFile('future1.epub', 'r') as z:
        content = z.read('text/part0000_split_000.html').decode('utf-8')
        
        lines = content.split('\n')
        print('Full line 9:')
        if len(lines) > 8:
            print(repr(lines[8]))
        
        print('\nCharacter at position 128:')
        print(repr(content[120:140]))
        
        print('\nFull content around line 9:')
        for i, line in enumerate(lines[6:12], 7):
            print(f'{i}: {repr(line)}')
        
        print('\nFirst 200 characters of the file:')
        print(repr(content[:200]))

if __name__ == "__main__":
    examine_file()