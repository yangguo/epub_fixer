#!/usr/bin/env python3
"""Compatibility import for the canonical deterministic EPUB fixer.

The repository used to carry a second, older copy of the fixer here. Keeping
one implementation prevents the CLI and OpenAI Agent SDK from applying
different EPUB 2/3 and cover rules to the same book.
"""

from epub_master_fixer import (
    SUPPORTED_TARGET_VERSIONS,
    build_fragment_index,
    detect_epub_version,
    extract_epub,
    find_opf_file,
    fix_cover_metadata,
    fix_css_file,
    fix_epub,
    fix_fragment_identifiers,
    fix_html_content,
    fix_invalid_aria_idrefs,
    fix_invalid_id_attributes,
    fix_missing_file_references,
    fix_ncx_file,
    fix_ncx_identifier,
    fix_opf_file,
    process_file,
    repack_epub,
    resolve_target_version,
    validate_and_fix,
)


__all__ = [
    "SUPPORTED_TARGET_VERSIONS",
    "build_fragment_index",
    "detect_epub_version",
    "extract_epub",
    "find_opf_file",
    "fix_cover_metadata",
    "fix_css_file",
    "fix_epub",
    "fix_fragment_identifiers",
    "fix_html_content",
    "fix_invalid_aria_idrefs",
    "fix_invalid_id_attributes",
    "fix_missing_file_references",
    "fix_ncx_file",
    "fix_ncx_identifier",
    "fix_opf_file",
    "process_file",
    "repack_epub",
    "resolve_target_version",
    "validate_and_fix",
]


if __name__ == "__main__":
    from epub_master_fixer import main

    main()
