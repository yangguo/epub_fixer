import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import JSZip from "jszip";
import fixEpub from "./epubFixer.js";

const MAX_READ_BYTES = 15 * 1024 * 1024; // 15 MB guard for uploaded EPUBs
const OUTPUT_DIR = path.join(os.tmpdir(), "epub-fixer");

function sanitizeOutputName(outputName) {
  if (!outputName) return null;
  const cleaned = outputName
    .replace(/[/\\]+/g, "_")
    .replace(/[^A-Za-z0-9._-]/g, "_")
    .replace(/^_+|_+$/g, "");
  if (!cleaned) return null;
  const parsed = path.parse(cleaned);
  const base = parsed.name.replace(/^\.+/, "");
  return `${base || "epub_fixed"}.epub`;
}

export function deriveOutputPath(epubPath, override) {
  const safeOverride = sanitizeOutputName(override);
  const parsed = path.parse(epubPath);
  const base = parsed.name.endsWith("_fixed") ? parsed.name : `${parsed.name}_fixed`;
  const filename = safeOverride || `${base}${parsed.ext || ".epub"}`;
  return path.join(OUTPUT_DIR, filename);
}

export async function writeTempEpub(buffer) {
  if (!buffer || !buffer.length) throw new Error("Empty EPUB payload.");
  const tmpPath = path.join(os.tmpdir(), `epub-${randomUUID()}.epub`);
  await fs.writeFile(tmpPath, buffer);
  return tmpPath;
}

export async function fetchEpubFromUrl(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Download failed (${resp.status})`);
  const arrBuf = await resp.arrayBuffer();
  if (!arrBuf.byteLength) throw new Error("Downloaded EPUB was empty.");
  return Buffer.from(arrBuf);
}

export async function parseEpubPayload(payload) {
  if (payload.epub_base64) {
    return Buffer.from(payload.epub_base64, "base64");
  }
  if (payload.epub_url) {
    return fetchEpubFromUrl(payload.epub_url);
  }
  if (payload.epub_path) {
    throw new Error("epub_path is disabled. Use epub_url or epub_base64.");
  }
  // NOTE: epub_path is intentionally not supported in the public API to prevent
  // server-side file disclosure. Users must provide epub_base64 or epub_url.
  throw new Error("Provide epub_url or epub_base64.");
}

export async function validateEpubStructure(epubPath) {
  const result = {
    success: false,
    epub_path: epubPath,
    has_errors: null,
    error_count: null,
    warning_count: null,
    errors: [],
    warnings: [],
    note: "Structural validation only (mimetype + container.xml). Full epubcheck not available in Node runtime.",
  };

  try {
    const buffer = await fs.readFile(epubPath);
    if (buffer.length > MAX_READ_BYTES) {
      result.warnings.push("Validation truncated: file larger than 15 MB limit.");
    }
    const zip = await JSZip.loadAsync(buffer);
    const mimetype = zip.file("mimetype");
    if (!mimetype) {
      result.errors.push("Missing mimetype file.");
    } else {
      const content = await mimetype.async("string");
      if (content.trim() !== "application/epub+zip") {
        result.errors.push("Invalid mimetype contents.");
      }
    }
    const hasContainer = !!zip.file("META-INF/container.xml");
    if (!hasContainer) {
      result.errors.push("Missing META-INF/container.xml");
    }
    result.has_errors = result.errors.length > 0;
    result.error_count = result.errors.length;
    result.warning_count = result.warnings.length;
    result.success = result.errors.length === 0;
  } catch (err) {
    result.errors.push(`Zip parse failed: ${err.message}`);
  }

  return result;
}

export async function applyRuleBasedFix(epubPath, outputPath) {
  const target = deriveOutputPath(epubPath, outputPath);
  const result = {
    success: false,
    epub_path: epubPath,
    output_path: target,
    errors: [],
    notes: [],
    fixes: [],
  };

  try {
    // Read the EPUB file
    const buffer = await fs.readFile(epubPath);

    // Apply the full EPUB fixer
    const fixResult = await fixEpub(buffer);

    // Write the fixed EPUB
    await fs.mkdir(path.dirname(target), { recursive: true });
    await fs.writeFile(target, fixResult.buffer);

    result.success = true;
    result.fixes = fixResult.fixes;
    result.notes.push(`Applied ${fixResult.fixes.length} fixes to EPUB files.`);

    if (fixResult.errors.length > 0) {
      result.notes.push(`Encountered ${fixResult.errors.length} non-fatal errors during fixing.`);
      result.errors.push(...fixResult.errors);
    }
  } catch (err) {
    result.errors.push(`Fix failed: ${err.message}`);
  }

  return result;
}

export async function encodeFileBase64(filePath, limitBytes) {
  const info = { data: null, truncated: false, errors: [] };
  try {
    const stats = await fs.stat(filePath);
    if (stats.size > limitBytes) info.truncated = true;
    const buffer = await fs.readFile(filePath);
    info.data = buffer.slice(0, limitBytes).toString("base64");
  } catch (err) {
    info.errors.push(err.message);
  }
  return info;
}

export async function cleanupTemp(paths) {
  await Promise.all(
    paths.map(async (p) => {
      if (!p) return;
      try {
        await fs.unlink(p);
      } catch {
        /* noop */
      }
    })
  );
}
