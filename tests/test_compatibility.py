import unittest
import tempfile
import zipfile
from pathlib import Path

from epub_master_fixer import (
    fix_epub,
    fix_fragment_identifiers,
    fix_html_content,
    fix_opf_file,
)


class CompatibilityTests(unittest.TestCase):
    def test_epub3_content_keeps_semantic_markup_by_default(self):
        content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops">'
            '<body><section epub:type="chapter" aria-label="Intro" '
            'role="doc-chapter"><nav epub:type="toc">Contents</nav>'
            '</section></body></html>'
        )

        repaired = fix_html_content(content)

        self.assertIn('<section ', repaired)
        self.assertIn('epub:type="chapter"', repaired)
        self.assertIn('aria-label="Intro"', repaired)
        self.assertIn('role="doc-chapter"', repaired)
        self.assertIn('<nav epub:type="toc">', repaired)

    def test_epub3_repair_preserves_header_and_removes_only_broken_aria_idrefs(self):
        content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops">'
            '<head><title>Example</title></head><body>'
            '<header id="heading"><h1>Title</h1></header>'
            '<section aria-labelledby="heading missing" aria-label="Keep">Text</section>'
            '</body></html>'
        )

        repaired = fix_html_content(content)

        self.assertIn('<header id="heading">', repaired)
        self.assertIn('aria-labelledby="heading"', repaired)
        self.assertIn('aria-label="Keep"', repaired)
        self.assertNotIn('missing', repaired)

    def test_epub2_target_explicitly_downgrades_semantic_markup(self):
        content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops">'
            '<body><section epub:type="chapter" aria-label="Intro" '
            'role="doc-chapter"><nav epub:type="toc">Contents</nav>'
            '</section></body></html>'
        )

        repaired = fix_html_content(content, target_version="epub2")

        self.assertNotIn('<section', repaired)
        self.assertNotIn('epub:type="chapter"', repaired)
        self.assertNotIn('aria-label="Intro"', repaired)
        self.assertNotIn('role="doc-chapter"', repaired)
        self.assertIn('<div>', repaired)

    def test_id_renames_update_local_fragment_and_aria_references(self):
        content = (
            '<html xmlns="http://www.w3.org/1999/xhtml">'
            '<head><title>Example</title></head><body>'
            '<h2 id="2:heading">Title</h2>'
            '<a href="#2:heading" aria-labelledby="2:heading">Link</a>'
            '</body></html>'
        )

        repaired = fix_html_content(content)

        self.assertIn('id="id_2_heading"', repaired)
        self.assertIn('href="#id_2_heading"', repaired)
        self.assertIn('aria-labelledby="id_2_heading"', repaired)

    def test_cross_document_fragment_is_rewritten_after_target_id_rename(self):
        source = '<a href="chapter.xhtml#2:section">Valid</a>'
        fragment_index = {"Text/chapter.xhtml": {"2:section"}}
        fragment_rewrites = {
            "Text/chapter.xhtml": {"2:section": "id_2_section"}
        }

        repaired = fix_fragment_identifiers(
            source,
            "Text/source.xhtml",
            fragment_index,
            fragment_rewrites=fragment_rewrites,
        )

        self.assertEqual('<a href="chapter.xhtml#id_2_section">Valid</a>', repaired)

    def test_epub2_opf_mode_preserves_page_map_and_drops_epub3_cover_property(self):
        opf = """<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Example</dc:title>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest><item id="My_Cover" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/></manifest>
  <spine page-map="page-map"><itemref idref="My_Cover"/></spine>
</package>"""

        repaired = fix_opf_file(opf, target_version="epub2")

        self.assertIn('page-map="page-map"', repaired)
        self.assertIn('name="cover" content="My_Cover"', repaired)
        self.assertNotIn('properties="cover-image"', repaired)

    def test_cover_metadata_points_to_existing_manifest_item(self):
        opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Example</dc:title>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="My_Cover" href="images/cover.jpg" media-type="image/jpeg"
          properties="cover-image"/>
  </manifest>
  <spine/>
</package>
"""

        repaired = fix_opf_file(opf)

        self.assertIn('<meta name="cover" content="My_Cover"/>', repaired)
        self.assertIn('id="My_Cover"', repaired)
        self.assertIn('properties="cover-image"', repaired)

    def test_cover_metadata_follows_normalized_manifest_id(self):
        opf = """<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Example</dc:title>
    <meta name="cover" content="2:cover"/>
  </metadata>
  <manifest><item id="2:cover" href="images/front.jpg" media-type="image/jpeg" properties="cover-image"/></manifest>
  <spine/>
</package>"""

        repaired = fix_opf_file(opf)

        self.assertIn('id="id_2_cover"', repaired)
        self.assertIn('content="id_2_cover"', repaired)

    def test_explicit_target_must_match_declared_package_version(self):
        opf = '<package xmlns="http://www.idpf.org/2007/opf" version="3.0"/>'

        with self.assertRaises(ValueError):
            fix_opf_file(opf, target_version="epub2")

    def test_cross_document_fragment_is_removed_only_when_target_is_known_broken(self):
        source = '<a href="chapter.xhtml#section-1">Valid</a>'
        fragment_index = {
            "Text/source.xhtml": {"source-id"},
            "Text/chapter.xhtml": {"section-1"},
        }

        repaired = fix_fragment_identifiers(
            source,
            "Text/source.xhtml",
            fragment_index,
        )
        self.assertEqual(source, repaired)

        broken = '<a href="chapter.xhtml#missing">Broken</a>'
        repaired_broken = fix_fragment_identifiers(
            broken,
            "Text/source.xhtml",
            fragment_index,
        )
        self.assertEqual('<a href="chapter.xhtml">Broken</a>', repaired_broken)

    def test_sdk_fixer_keeps_the_same_epub3_default(self):
        from openai_agent_sdk.rule_fixer import fix_html_content as sdk_fix_html_content

        content = (
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops">'
            '<body><section epub:type="chapter">Text</section>'
            '</body></html>'
        )

        self.assertEqual(fix_html_content(content), sdk_fix_html_content(content))

    def test_fix_epub_auto_repairs_cover_without_downgrading_epub3(self):
        files = {
            "mimetype": "application/epub+zip",
            "META-INF/container.xml": """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""",
            "OEBPS/content.opf": """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Example</dc:title>
    <meta name="cover" content="cover-image"/>
  </metadata>
  <manifest>
    <item id="My_Cover" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="chapter"/></spine>
</package>
""",
            "OEBPS/chapter.xhtml": """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head><title>Example</title></head>
  <body><section epub:type="chapter" aria-label="Chapter"><p>Text</p></section></body>
</html>
""",
        }

        with tempfile.TemporaryDirectory(prefix="epub-fixer-test-") as temp_dir:
            epub_path = Path(temp_dir) / "example.epub"
            with zipfile.ZipFile(epub_path, "w") as archive:
                archive.writestr("mimetype", files["mimetype"], compress_type=zipfile.ZIP_STORED)
                for name, content in files.items():
                    if name != "mimetype":
                        archive.writestr(name, content)

            fix_epub(str(epub_path))

            with zipfile.ZipFile(epub_path) as archive:
                opf = archive.read("OEBPS/content.opf").decode("utf-8")
                chapter = archive.read("OEBPS/chapter.xhtml").decode("utf-8")

            self.assertIn('name="cover" content="My_Cover"', opf)
            self.assertIn('properties="cover-image"', opf)
            self.assertIn('<section epub:type="chapter"', chapter)
            self.assertIn('aria-label="Chapter"', chapter)

    def test_fix_epub_rewrites_cross_document_fragment_after_id_rename(self):
        files = {
            "mimetype": "application/epub+zip",
            "META-INF/container.xml": """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""",
            "OEBPS/content.opf": """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Example</dc:title></metadata>
  <manifest>
    <item id="source" href="source.xhtml" media-type="application/xhtml+xml"/>
    <item id="target" href="target.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="source"/><itemref idref="target"/></spine>
</package>
""",
            "OEBPS/source.xhtml": """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Source</title></head>
<body><p><a href="target.xhtml#2:section">Target</a></p></body></html>
""",
            "OEBPS/target.xhtml": """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Target</title></head>
<body><h2 id="2:section">Target</h2></body></html>
""",
        }

        with tempfile.TemporaryDirectory(prefix="epub-fixer-link-test-") as temp_dir:
            epub_path = Path(temp_dir) / "example.epub"
            with zipfile.ZipFile(epub_path, "w") as archive:
                archive.writestr("mimetype", files["mimetype"], compress_type=zipfile.ZIP_STORED)
                for name, content in files.items():
                    if name != "mimetype":
                        archive.writestr(name, content)

            fix_epub(str(epub_path))

            with zipfile.ZipFile(epub_path) as archive:
                source = archive.read("OEBPS/source.xhtml").decode("utf-8")
                target = archive.read("OEBPS/target.xhtml").decode("utf-8")

            self.assertIn('href="target.xhtml#id_2_section"', source)
            self.assertIn('id="id_2_section"', target)


if __name__ == "__main__":
    unittest.main()
