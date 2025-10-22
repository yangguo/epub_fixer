#!/usr/bin/env python3

# Calculate hex values for charset patterns
bad_pattern = 'charset="utf-8""'  # with extra quote at end
good_pattern = 'charset="utf-8"'   # correct pattern

print('Bad pattern:', repr(bad_pattern))
print('Bad hex:', bad_pattern.encode().hex())
print('Good pattern:', repr(good_pattern))
print('Good hex:', good_pattern.encode().hex())

# Also check the full meta tag patterns with />
bad_meta = 'charset="utf-8""/>'
good_meta = 'charset="utf-8"/>'

print('\nBad meta with />:', repr(bad_meta))
print('Bad meta hex:', bad_meta.encode().hex())
print('Good meta with />:', repr(good_meta))
print('Good meta hex:', good_meta.encode().hex())

# Show the difference
print('\nHex difference:')
print('Bad: ', bad_meta.encode().hex())
print('Good:', good_meta.encode().hex())
print('Extra bytes in bad:', set(bad_meta.encode().hex()) - set(good_meta.encode().hex()))