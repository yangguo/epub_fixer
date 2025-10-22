import zipfile

with zipfile.ZipFile('future1.epub', 'r') as epub:
    content = epub.read('text/part0000_split_000.html').decode('utf-8')
    lines = content.split('\n')
    
    print('Line 9 length:', len(lines[8]))
    print('Line 9 (first 200 chars):')
    print(repr(lines[8][:200]))
    print('\nLine 9 around position 200:')
    print(repr(lines[8][190:210]))
    
    # Look for the specific error at position 206
    print('\nCharacters around position 206:')
    print(repr(lines[8][200:220]))