#!/usr/bin/env python3
"""Fix unclosed <br> tags inside an EPUB's XHTML/HTML files.

Creates a backup copy and writes a new EPUB with fixed files named
`<original>_fixed.epub` by default.
"""
from __future__ import annotations
import argparse
import zipfile
import shutil
import re
from pathlib import Path
import tempfile


def fix_br_tags(text: str) -> str:
    # Replace any <br ...> that is NOT already self-closed (<br/> or <br />)
    # Preserve attributes.
    def repl(m):
        attrs = m.group(1) or ''
        if attrs.strip().endswith('/'):
            return m.group(0)  # already self-closed
        return '<br' + attrs.rstrip() + ' />'

    return re.sub(r'(?i)<br\b([^>]*)>', repl, text)


def process_epub(epub_path: Path, out_path: Path) -> int:
    changed = 0
    with zipfile.ZipFile(epub_path, 'r') as zin, zipfile.ZipFile(out_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            name = item.filename
            lower = name.lower()
            if lower.endswith(('.xhtml', '.html', '.htm')):
                try:
                    text = data.decode('utf-8')
                except Exception:
                    try:
                        text = data.decode('cp1251')
                    except Exception:
                        text = data.decode('utf-8', errors='replace')
                new = fix_br_tags(text)
                if new != text:
                    changed += 1
                    data = new.encode('utf-8')
            zout.writestr(item, data)
    return changed


def main() -> None:
    p = argparse.ArgumentParser(description='Fix unclosed <br> tags inside an EPUB')
    p.add_argument('epub', type=Path, help='EPUB file to fix')
    p.add_argument('--inplace', action='store_true', help='Overwrite original (backup will be created)')
    args = p.parse_args()
    epub = args.epub
    if not epub.exists():
        raise SystemExit(f'File not found: {epub}')

    out_path = epub.with_name(epub.stem + '_fixed' + epub.suffix)
    backup_path = epub.with_name(epub.stem + '_backup' + epub.suffix)

    # create backup
    shutil.copy2(epub, backup_path)

    changed = process_epub(epub, out_path)

    if args.inplace:
        # replace original (keep backup)
        shutil.move(out_path, epub)
        print(f'Fixed EPUB written inplace to {epub}; backup at {backup_path}; files changed: {changed}')
    else:
        print(f'Fixed EPUB written to {out_path}; backup at {backup_path}; files changed: {changed}')


if __name__ == '__main__':
    main()
