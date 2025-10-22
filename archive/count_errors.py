import re

with open('output.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Count different error types
fatal_errors = len(re.findall(r'FATAL\([^)]+\)', content))
errors = len(re.findall(r'ERROR\([^)]+\)', content))
warnings = len(re.findall(r'WARNING\([^)]+\)', content))

print(f"Final epubcheck results:")
print(f"Fatal errors: {fatal_errors}")
print(f"Errors: {errors}")
print(f"Warnings: {warnings}")
print(f"Total issues: {fatal_errors + errors + warnings}")

# Count specific error types
rsc_016_errors = len(re.findall(r'FATAL\(RSC-016\)', content))
rsc_005_errors = len(re.findall(r'ERROR\(RSC-005\)', content))
rsc_007_errors = len(re.findall(r'ERROR\(RSC-007\)', content))
rsc_012_errors = len(re.findall(r'ERROR\(RSC-012\)', content))

print(f"\nBreakdown by error type:")
print(f"FATAL(RSC-016) - Malformed HTML: {rsc_016_errors}")
print(f"ERROR(RSC-005) - Text not allowed: {rsc_005_errors}")
print(f"ERROR(RSC-007) - Referenced resource not found: {rsc_007_errors}")
print(f"ERROR(RSC-012) - Fragment identifier not defined: {rsc_012_errors}")

# Show the final status line
lines = content.split('\n')
for line in lines[-10:]:
    if 'Check finished' in line:
        print(f"\nFinal status: {line}")
        break