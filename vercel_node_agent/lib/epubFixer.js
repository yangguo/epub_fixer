/**
 * EPUB Master Fixer - JavaScript Port
 * Handles 95% of EPUB validation issues
 *
 * Fixes:
 * - NCX identifier mismatch with OPF
 * - Unclosed anchor tags (especially in <sup> elements)
 * - Fragment identifiers pointing to non-existent IDs
 * - NCX IDs with colons (invalid XML names)
 * - Missing class attribute on pageList
 * - PlayOrder conflicts and gaps
 * - Page-map attribute in OPF spine (EPUB 2.0.1)
 * - Invalid dir attributes
 * - Mangled p tags
 * - Missing alt attributes on images
 * - HTML5 to EPUB 2 element conversion
 */

import JSZip from "jszip";
import path from "node:path";

/**
 * Main function to fix an EPUB buffer
 * @param {Buffer} epubBuffer - The EPUB file as a Buffer
 * @returns {Promise<{buffer: Buffer, fixes: string[], errors: string[]}>}
 */
export async function fixEpub(epubBuffer) {
  const fixes = [];
  const errors = [];

  try {
    const zip = await JSZip.loadAsync(epubBuffer);

    // First pass: find and read OPF to get identifier
    let opfContent = null;
    let opfPath = null;
    for (const [filePath, file] of Object.entries(zip.files)) {
      if (filePath.endsWith(".opf") && !file.dir) {
        opfContent = await file.async("string");
        opfPath = filePath;
        break;
      }
    }

    // Build fragment index for validating NCX references
    const fragmentIndex = await buildFragmentIndex(zip);

    // Process all files
    for (const [filePath, file] of Object.entries(zip.files)) {
      if (file.dir) continue;

      const ext = path.extname(filePath).toLowerCase();
      if (![".xhtml", ".html", ".htm", ".ncx", ".opf", ".xml", ".css"].includes(ext)) {
        continue;
      }

      try {
        let content = await file.async("string");
        const original = content;

        if (ext === ".ncx") {
          content = fixNcxFile(content, opfContent, fragmentIndex, filePath);
        } else if (ext === ".opf") {
          content = fixOpfFile(content);
        } else if (ext === ".css") {
          content = fixCssFile(content);
        } else if (ext === ".xml" && !content.toLowerCase().includes("<html")) {
          // Skip non-HTML XML files
          continue;
        } else {
          content = fixHtmlContent(content);
          content = fixFragmentIdentifiers(content);
        }

        if (content !== original) {
          zip.file(filePath, content);
          fixes.push(`Fixed: ${filePath}`);
        }
      } catch (err) {
        errors.push(`Error processing ${filePath}: ${err.message}`);
      }
    }

    // Repack with proper mimetype handling
    const fixedBuffer = await repackEpub(zip);
    return { buffer: fixedBuffer, fixes, errors };
  } catch (err) {
    errors.push(`EPUB processing failed: ${err.message}`);
    return { buffer: epubBuffer, fixes, errors };
  }
}

/**
 * Repack EPUB with mimetype as first uncompressed entry
 */
async function repackEpub(zip) {
  const newZip = new JSZip();

  // Add mimetype first, uncompressed
  const mimetypeFile = zip.file("mimetype");
  if (mimetypeFile) {
    const mimetypeContent = await mimetypeFile.async("string");
    newZip.file("mimetype", mimetypeContent, { compression: "STORE" });
  } else {
    newZip.file("mimetype", "application/epub+zip", { compression: "STORE" });
  }

  // Add all other files
  for (const [filePath, file] of Object.entries(zip.files)) {
    if (filePath === "mimetype" || file.dir) continue;
    const content = await file.async("nodebuffer");
    newZip.file(filePath, content);
  }

  return newZip.generateAsync({
    type: "nodebuffer",
    compression: "DEFLATE",
    compressionOptions: { level: 9 },
  });
}

/**
 * Build index of IDs in HTML files for fragment validation
 */
async function buildFragmentIndex(zip) {
  const index = {};
  for (const [filePath, file] of Object.entries(zip.files)) {
    if (file.dir) continue;
    const ext = path.extname(filePath).toLowerCase();
    if (![".xhtml", ".html", ".htm", ".xml"].includes(ext)) continue;

    try {
      const content = await file.async("string");
      if (!content.toLowerCase().includes("<html")) continue;
      const ids = new Set(content.match(/id="([^"]+)"/gi)?.map((m) => m.slice(4, -1)) || []);
      index[filePath] = ids;
    } catch {
      // Skip files that can't be read
    }
  }
  return index;
}

// ============ HTML Fixes ============

function fixHtmlContent(content) {
  // CRITICAL: Fix mangled tags FIRST
  content = fixMangledPTags(content);

  // Fix unclosed tags
  content = fixUnclosedAnchorTags(content);
  content = fixUnclosedPTags(content);

  // Fix invalid ID attributes
  content = fixInvalidIdAttributes(content);

  // Fix dir attributes
  content = fixDirAttributes(content);

  // Fix malformed head tags
  content = content.replace(/<\/head[^>]*>/gi, "</head>");

  // Fix meta value attributes
  content = fixMetaValueAttributes(content);

  // Fix HTML namespace
  content = fixHtmlNamespace(content);

  // Fix structural issues
  content = fixStructuralIssues(content);

  // EPUB 2.0.1 compatibility fixes
  const replacements = [
    // Remove EPUB 3 specific attributes
    [/\s+epub:type="[^"]*"/gi, ""],
    [/\s+epub:prefix="[^"]*"/gi, ""],
    [/\s+data-number="[^"]*"/gi, ""],
    [/\s+hidden(?:="[^"]*")?/gi, ""],
    [/\s+aria-[a-z-]*="[^"]*"/gi, ""],
    [/\s+role="[^"]*"/gi, ""],

    // HTML5 to HTML4 element conversion
    [/<section([^>]*)>/gi, "<div$1>"],
    [/<\/section>/gi, "</div>"],
    [/<nav([^>]*)>/gi, "<div$1>"],
    [/<\/nav>/gi, "</div>"],
    [/<figure([^>]*)>/gi, "<div$1>"],
    [/<\/figure>/gi, "</div>"],
    [/<figcaption([^>]*)>/gi, "<div$1>"],
    [/<\/figcaption>/gi, "</div>"],
    [/<aside([^>]*)>/gi, "<div$1>"],
    [/<\/aside>/gi, "</div>"],
    [/<header([^>]*)>/gi, "<div$1>"],
    [/<\/header>/gi, "</div>"],

    // Fix style tags
    [/<style(?![^>]*type=)([^>]*)>/gi, '<style type="text/css"$1>'],
  ];

  for (const [pattern, replacement] of replacements) {
    content = content.replace(pattern, replacement);
  }

  // Fix malformed sup tags
  content = fixMalformedSupTags(content);

  // Remove empty attributes
  content = content.replace(/\s+\w+=""/g, "");

  // Fix incomplete body
  content = fixIncompleteBody(content);

  // Fix missing </body> tags
  content = fixMissingBodyClose(content);

  // Wrap blockquote text and ensure image alt attributes
  content = wrapBlockquoteText(content);
  content = ensureImageAltAttributes(content);

  return content;
}

function fixMangledPTags(content) {
  // Fix tags like <ppubli -> <p class="publi"
  return content.replace(/<p([a-z0-9]+)/g, '<p class="$1"');
}

function fixUnclosedPTags(content) {
  // Fix corrupted closing tags
  content = content.replace(/<\/p>\s*s="([^"]*)">/g, '<p class="$1">');

  const pattern = /<p(?=[\s>])[^>]*>|<\/p>/gi;
  const segments = [];
  let lastIndex = 0;
  let openCount = 0;
  let match;

  const regex = new RegExp(pattern);
  while ((match = regex.exec(content)) !== null) {
    segments.push(content.slice(lastIndex, match.index));
    const tag = match[0];
    if (tag.toLowerCase().startsWith("</p")) {
      if (openCount > 0) {
        openCount--;
        segments.push(tag);
      }
      // Skip unmatched closing tags
    } else {
      openCount++;
      segments.push(tag);
    }
    lastIndex = regex.lastIndex;
  }
  segments.push(content.slice(lastIndex));
  content = segments.join("");

  if (openCount > 0) {
    content = content.replace(/<\/body>/i, "</p>".repeat(openCount) + "</body>");
  }

  return content;
}

function fixInvalidIdAttributes(content) {
  return content.replace(/\bid\s*=\s*"([^"]*)"/gi, (match, idValue) => {
    if (!idValue) return match;
    let fixed = idValue;
    // Replace colons with underscores
    if (fixed.includes(":")) {
      fixed = fixed.replace(/:/g, "_");
    }
    // If ID starts with a number, prefix with 'id_'
    if (fixed && /^\d/.test(fixed)) {
      fixed = `id_${fixed}`;
    }
    return `id="${fixed}"`;
  });
}

function fixDirAttributes(content) {
  return content.replace(/dir="([^"]*)"/gi, (match, dirValue) => {
    const lower = dirValue.toLowerCase();
    if (lower === "ltr" || lower === "rtl") return match;
    return 'dir="ltr"';
  });
}

function fixMetaValueAttributes(content) {
  return content.replace(/<meta\b[^>]*>/gi, (tag) => {
    const valueMatch = tag.match(/\bvalue\s*=\s*"([^"]*)"/i);
    if (!valueMatch) return tag;
    const val = valueMatch[1];
    if (/\bcontent\s*=/i.test(tag)) {
      return tag.replace(/\s*\bvalue\s*=\s*"[^"]*"/i, "");
    }
    return tag.replace(/\bvalue\s*=\s*"[^"]*"/i, `content="${val}"`);
  });
}

function fixHtmlNamespace(content) {
  return content.replace(/<html[^>]*>/gi, (htmlTag) => {
    if (!htmlTag.includes("xmlns=")) {
      htmlTag = htmlTag.replace(/<html/i, '<html xmlns="http://www.w3.org/1999/xhtml"');
    }
    // Remove problematic attributes
    htmlTag = htmlTag.replace(/\s+class="[^"]*"/gi, "");
    htmlTag = htmlTag.replace(/\s+epub:prefix="[^"]*"/gi, "");
    return htmlTag;
  });
}

function fixStructuralIssues(content) {
  // Move h1 elements from head to body
  const headMatch = content.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  if (headMatch) {
    let headContent = headMatch[1];
    const h1Elements = headContent.match(/<h1[^>]*>[\s\S]*?<\/h1>/gi) || [];
    if (h1Elements.length > 0) {
      headContent = headContent.replace(/<h1[^>]*>[\s\S]*?<\/h1>/gi, "");
      content = content.replace(headMatch[0], `<head>${headContent}</head>`);
      for (const h1 of h1Elements) {
        content = content.replace(/<body[^>]*>/i, `<body>\n${h1}`);
      }
    }
  }

  // Ensure head has a title element
  const headMatch2 = content.match(/<head[^>]*>([\s\S]*?)<\/head>/i);
  if (headMatch2) {
    const headContent = headMatch2[1];
    if (!/<title[^>]*>[\s\S]*?<\/title>/i.test(headContent)) {
      content = content.replace(
        headMatch2[0],
        `<head>${headContent}\n<title>Document</title></head>`
      );
    }
  }

  return content;
}

function fixMalformedSupTags(content) {
  // <sup>text</a></sup> -> <sup>text</sup>
  content = content.replace(/<sup([^>]*)>([^<]*)<\/a><\/sup>/gi, "<sup$1>$2</sup>");
  // </a></a></sup> -> </a></sup>
  content = content.replace(/<\/a><\/a><\/sup>/gi, "</a></sup>");
  return content;
}

function fixIncompleteBody(content) {
  // Fix empty body elements
  return content.replace(/<body[^>]*>(\s*)<\/body>/gi, (match, whitespace) => {
    if (!whitespace.trim()) {
      return match.replace(whitespace, "<p>&nbsp;</p>");
    }
    return match;
  });
}

function fixMissingBodyClose(content) {
  const bodyOpen = (content.match(/<body[^>]*(?<!\/)>/gi) || []).length;
  const bodyClose = (content.match(/<\/body>/gi) || []).length;

  if (bodyClose < bodyOpen) {
    const missing = bodyOpen - bodyClose;
    const closes = "</body>".repeat(missing);
    if (content.includes("</html>")) {
      content = content.replace(/<\/html>/i, `${closes}</html>`);
    } else {
      content = content.trimEnd() + closes;
    }
  }
  return content;
}

function fixUnclosedAnchorTags(content) {
  // Pattern 1: <sup ...><a href="...">text</sup> -> ensure </a>
  content = content.replace(
    /<sup([^>]*)><a\s+([^>]*)>([^<]*)<\/sup>/gi,
    "<sup$1><a $2>$3</a></sup>"
  );

  // Pattern 2: Generic anchor closing before block elements
  content = closeAnchorBeforeBlock(content);

  // Balance anchor tags
  content = balanceAnchorTags(content);

  return content;
}

function closeAnchorBeforeBlock(content) {
  const pattern = /(<a\b[^>]*>)([^<]*?)(<\/(?:sup|em|strong|i|b|span|p|div|li|h[1-6]|blockquote)>)/gi;
  let prev = "";
  while (prev !== content) {
    prev = content;
    content = content.replace(pattern, "$1$2</a>$3");
  }
  return content;
}

function balanceAnchorTags(content) {
  const pattern = /<a\b[^>]*>|<\/a>/gi;
  const segments = [];
  let lastIndex = 0;
  let openCount = 0;
  let match;

  const regex = new RegExp(pattern);
  while ((match = regex.exec(content)) !== null) {
    segments.push(content.slice(lastIndex, match.index));
    const token = match[0];
    if (token.toLowerCase().startsWith("</a")) {
      if (openCount > 0) {
        openCount--;
        segments.push(token);
      }
      // Skip unmatched closing anchor
    } else {
      openCount++;
      segments.push(token);
    }
    lastIndex = regex.lastIndex;
  }
  segments.push(content.slice(lastIndex));
  let balanced = segments.join("");

  if (openCount > 0) {
    const closes = "</a>".repeat(openCount);
    if (balanced.includes("</body>")) {
      balanced = balanced.replace("</body>", closes + "</body>");
    } else {
      balanced += closes;
    }
  }

  return balanced;
}

function wrapBlockquoteText(content) {
  const blockLevelPattern = /^\s*<(?:address|blockquote|del|div|dl|h[1-6]|hr|ins|noscript|ol|p|pre|script|table|ul)\b/i;

  return content.replace(
    /(<blockquote[^>]*>)([\s\S]*?)(<\/blockquote>)/gi,
    (match, openTag, inner, closeTag) => {
      const stripped = inner.trim();
      if (!stripped) {
        return `${openTag}<p>&nbsp;</p>${closeTag}`;
      }
      if (blockLevelPattern.test(stripped)) {
        return match;
      }
      return `${openTag}\n    <p>${stripped}</p>\n${closeTag}`;
    }
  );
}

function ensureImageAltAttributes(content) {
  return content.replace(/<img\b[^>]*>/gi, (tag) => {
    if (/\balt\s*=/i.test(tag)) return tag;

    const srcMatch = tag.match(/\bsrc\s*=\s*"([^"]*)"/i);
    let altValue = "Image";
    if (srcMatch) {
      const filename = path.basename(srcMatch[1]);
      const name = path.parse(filename).name.replace(/[_-]/g, " ").trim();
      altValue = name || "Image";
    }

    const closingMatch = tag.match(/\s*\/?>\s*$/);
    if (!closingMatch) return tag;

    let prefix = tag.slice(0, closingMatch.index).trimEnd();
    if (!prefix.endsWith(" ")) prefix += " ";
    return `${prefix}alt="${altValue}"${closingMatch[0]}`;
  });
}

function fixFragmentIdentifiers(content) {
  const existingIds = new Set(content.match(/id="([^"]+)"/g)?.map((m) => m.slice(4, -1)) || []);

  return content.replace(/href="([^"]*)"/g, (match, href) => {
    if (!href.includes("#")) return match;
    const parts = href.split("#");
    if (parts.length !== 2) return match;
    const [filePart, fragment] = parts;

    // Local reference check
    if (!filePart || filePart.match(/\.(xhtml|html|htm)$/i)) {
      if (fragment && !existingIds.has(fragment)) {
        return filePart ? `href="${filePart}"` : 'href="#"';
      }
    }
    return match;
  });
}

// ============ NCX Fixes ============

function fixNcxFile(content, opfContent, fragmentIndex, currentPath) {
  // Fix NCX identifier to match OPF
  if (opfContent) {
    const opfIdMatch = opfContent.match(/<dc:identifier[^>]*>([^<]+)<\/dc:identifier>/);
    if (opfIdMatch) {
      const correctId = opfIdMatch[1];
      content = content.replace(
        /(<meta\s+name="dtb:uid"\s+content=")[^"]*(")/,
        `$1${correctId}$2`
      );
    }
  }

  // Fix invalid XML IDs
  content = content.replace(/id="([^"]*)"/g, (match, idValue) => {
    let fixed = idValue;
    if (fixed && /^\d/.test(fixed)) {
      fixed = `id_${fixed}`;
    }
    if (fixed.includes(":")) {
      fixed = fixed.replace(/:/g, "_");
    }
    return `id="${fixed}"`;
  });

  // Fix pageList class attribute (ensure exactly one)
  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes("<pageList")) {
      const classCount = (lines[i].match(/class=/g) || []).length;
      if (classCount > 1) {
        lines[i] = lines[i].replace(/\s+class="[^"]*"/g, "");
        lines[i] = lines[i].replace("<pageList", '<pageList class="pageList"');
      } else if (classCount === 0) {
        lines[i] = lines[i].replace("<pageList", '<pageList class="pageList"');
      }
    }
  }
  content = lines.join("\n");

  // Fix playOrder - elements with same src must have same playOrder
  content = fixPlayOrder(content);

  // Remove fragment identifiers pointing to missing anchors
  if (fragmentIndex && currentPath) {
    const baseDir = path.dirname(currentPath);
    content = content.replace(
      /(<content\s+src=")([^"]*)(")/gi,
      (match, prefix, srcValue, suffix) => {
        if (!srcValue.includes("#")) return match;
        const [filePart, fragment] = srcValue.split("#");
        const normalizedTarget = path.join(baseDir, filePart).replace(/\\/g, "/");
        const ids = fragmentIndex[normalizedTarget];
        if (!fragment || !ids || !ids.has(fragment)) {
          return `${prefix}${filePart}${suffix}`;
        }
        return match;
      }
    );
  }

  return content;
}

function fixPlayOrder(content) {
  const lines = content.split("\n");
  const elements = [];

  // Collect all navPoint/pageTarget with their src
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes("playOrder=") && (lines[i].includes("navPoint") || lines[i].includes("pageTarget"))) {
      let src = null;
      for (let j = i; j < Math.min(i + 10, lines.length); j++) {
        const srcMatch = lines[j].match(/<content\s+src="([^"]*)"/);
        if (srcMatch) {
          src = srcMatch[1];
          break;
        }
      }
      elements.push({ lineIdx: i, src });
    }
  }

  // Build mapping: src -> playOrder
  const srcToOrder = new Map();
  let playOrder = 1;

  for (const { src } of elements) {
    if (src && !srcToOrder.has(src)) {
      srcToOrder.set(src, playOrder++);
    }
  }

  // Update playOrder values
  for (const { lineIdx, src } of elements) {
    if (src && srcToOrder.has(src)) {
      lines[lineIdx] = lines[lineIdx].replace(/playOrder="[^"]*"/, `playOrder="${srcToOrder.get(src)}"`);
    } else {
      lines[lineIdx] = lines[lineIdx].replace(/playOrder="[^"]*"/, `playOrder="${playOrder++}"`);
    }
  }

  return lines.join("\n");
}

// ============ OPF Fixes ============

function fixOpfFile(content) {
  // Remove page-map attribute from spine (not allowed in EPUB 2.0.1)
  content = content.replace(/<spine([^>]*)\s+page-map="[^"]*"([^>]*)>/g, "<spine$1$2>");

  // Remove fragment identifiers from manifest hrefs
  content = content.replace(/href="([^#]*)#[^"]*"/g, 'href="$1"');

  return content;
}

// ============ CSS Fixes ============

function fixCssFile(content) {
  // Remove @font-face rules with invalid src URLs
  content = content.replace(/@font-face\s*\{[^}]*src:\s*url\([^)]*XXXX[^)]*\)[^}]*\}/gi, "");

  // Remove malformed url() references
  content = content.replace(/src:\s*url\([^)]*XXXX[^)]*\);/gi, "");

  return content;
}

export default fixEpub;
