/**
 * render main — the exporter entry point.
 *
 * Reads a built deck (deck + image assets from the build pass), renders the
 * single self-contained HTML, and writes it. This is the v1 artefact: one
 * file that runs offline with zero network requests. With --pdf it also
 * prints the same bytes to a slide-sized PDF (phase 14).
 */

import { readFileSync, writeFileSync } from 'node:fs';

import type { Deck } from '@web/schema/generated/Deck.js';
import { renderDeckToHtml } from './export.jsx';
import { renderDeckToPdf } from './pdf.js';

type BuiltPayload = {
  deck: Deck;
  images?: Record<string, string>;
};

export function exportDeckFile(inputPath: string, outputPath: string): string {
  const raw = JSON.parse(readFileSync(inputPath, 'utf8')) as BuiltPayload;
  const html = renderDeckToHtml({ deck: raw.deck, images: raw.images });
  writeFileSync(outputPath, html, 'utf8');
  return outputPath;
}

export async function exportDeckPdf(inputPath: string, outputPath: string): Promise<string> {
  const raw = JSON.parse(readFileSync(inputPath, 'utf8')) as BuiltPayload;
  const pdf = await renderDeckToPdf({ deck: raw.deck, images: raw.images });
  writeFileSync(outputPath, pdf);
  return outputPath;
}

// CLI: node render/dist/main.js <built.json> <out.html> [--pdf <out.pdf>]
// Wrapped so the PDF path's await is not a top-level await (esbuild cannot
// bundle one to CJS).
const [, , inputPath, outputPath, pdfFlag, pdfPath] = process.argv;
if (inputPath && outputPath) {
  void (async () => {
    const out = exportDeckFile(inputPath, outputPath);
    console.log(`Exported ${out}`);
    if (pdfFlag === '--pdf' && pdfPath) {
      const pdf = await exportDeckPdf(inputPath, pdfPath);
      console.log(`Exported PDF ${pdf}`);
    }
  })();
}
