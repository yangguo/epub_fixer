import zipfile

with zipfile.ZipFile('future1.epub', 'r') as epub:
    content = epub.read('text/part0000_split_000.html').decode('utf-8')
    lines = content.split('\n')
    
    print('Line 9 structure analysis:')
    line9 = lines[8]
    print(f'Length: {len(line9)}')
    
    print('\nFirst 200 chars:')
    print(repr(line9[:200]))
    
    print('\nAround position 165 (first li error):')
    print(repr(line9[150:180]))
    
    print('\nAround position 209 (URL error):')
    print(repr(line9[195:225]))
    
    # Count problematic elements
    li_count = line9.count('<li')
    ul_count = line9.count('<ul')
    ol_count = line9.count('<ol')
    
    print(f'\nElement counts:')
    print(f'<li> tags: {li_count}')
    print(f'<ul> tags: {ul_count}')
    print(f'<ol> tags: {ol_count}')
    
    # Look for malformed URLs
    import re
    malformed_urls = re.findall(r'href="[^"]*>[^"]*"', line9)
    print(f'\nMalformed URLs found: {len(malformed_urls)}')
    for i, url in enumerate(malformed_urls[:3]):
        print(f'  {i+1}: {url}')