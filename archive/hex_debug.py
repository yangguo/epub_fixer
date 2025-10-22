#!/usr/bin/env python3

def analyze_line_bytes(file_path, line_number):
    """Analyze the exact bytes of a specific line"""
    try:
        with open(file_path, 'rb') as f:
            lines = f.read().split(b'\n')
            
        if line_number <= len(lines):
            line_bytes = lines[line_number - 1]  # Convert to 0-based index
            
            print(f"Line {line_number} content:")
            print(f"Raw bytes: {line_bytes}")
            print(f"Hex: {line_bytes.hex()}")
            print(f"Decoded: {line_bytes.decode('utf-8', errors='replace')}")
            
            # Look for charset pattern
            charset_pos = line_bytes.find(b'charset=')
            if charset_pos != -1:
                print(f"\nCharset found at position {charset_pos}")
                # Show 20 bytes around charset
                start = max(0, charset_pos - 5)
                end = min(len(line_bytes), charset_pos + 25)
                segment = line_bytes[start:end]
                print(f"Context bytes: {segment}")
                print(f"Context hex: {segment.hex()}")
                print(f"Context decoded: {segment.decode('utf-8', errors='replace')}")
                
                # Show each character with its hex value
                print("\nByte-by-byte analysis:")
                for i, byte_val in enumerate(segment):
                    char = chr(byte_val) if 32 <= byte_val <= 126 else f'\\x{byte_val:02x}'
                    print(f"  {start + i:2d}: 0x{byte_val:02x} '{char}'")
            
        else:
            print(f"File only has {len(lines)} lines")
            
    except Exception as e:
        print(f"Error analyzing file: {e}")

def main():
    file_path = "final_meta_debug/titlepage.xhtml"
    line_number = 4
    
    print(f"=== Analyzing {file_path} line {line_number} ===")
    analyze_line_bytes(file_path, line_number)

if __name__ == "__main__":
    main()