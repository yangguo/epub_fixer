import zipfile

with zipfile.ZipFile('future1.epub', 'r') as epub:
    content = epub.read('text/part0000_split_000.html').decode('utf-8')
    lines = content.split('\n')
    
    print('Line 9 after fix:')
    line9 = lines[8]
    print(f'Length: {len(line9)}')
    
    print('\nFirst 200 chars:')
    print(repr(line9[:200]))
    
    print('\nLast 100 chars:')
    print(repr(line9[-100:]))
    
    # Check if we have nested <ul> tags
    ul_count = line9.count('<ul>')
    ul_close_count = line9.count('</ul>')
    print(f'\n<ul> tags: {ul_count}')
    print(f'</ul> tags: {ul_close_count}')
    
    # Check for malformed URLs
    if 'href="kindle:' in line9:
        print('\nURL fix successful - no more ">" in URLs')
    else:
        print('\nURL issue may still exist')