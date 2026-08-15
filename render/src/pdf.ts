/**
 * renderDeckToPdf — the PDF export path (phase 14).
 *
 * The PDF is a faithful print of the single-file HTML, not a screenshot
 * (14-pdf-export.md). The HTML is rendered by the same renderDeckToHtml the
 * CLI writes; Playwright loads those exact bytes and prints them. The print
 * CSS (@page, slide-sized pages, resting state) is already inside the HTML
 * (see PRINT_CSS in export.tsx), so the PDF and the HTML cannot drift — the
 * byte-identity guarantee extends to the print.
 *
 * Playwright is the documented print path (dependencies.md: "headless
 * Chromium for the screenshot service ... whose job is driving a browser").
 */

import { chromium } from 'playwright';

import { renderDeckToHtml } from './export.jsx';
import type { ExportInput } from './export.jsx';

export type PdfOptions = {
  /** Slide width in inches. Must match @page in the print CSS (16in 9in). */
  widthIn?: number;
  heightIn?: number;
};

export async function renderDeckToPdf(
  input: ExportInput,
  options: PdfOptions = {},
): Promise<Buffer> {
  const widthIn = options.widthIn ?? 16;
  const heightIn = options.heightIn ?? 9;
  const html = renderDeckToHtml(input);

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    // setContent with the exact HTML bytes: no base URL, no network, the
    // same bytes the CLI writes to disk.
    await page.setContent(html, { waitUntil: 'load' });
    const pdf = await page.pdf({
      width: `${widthIn}in`,
      height: `${heightIn}in`,
      printBackground: true,
      preferCSSPageSize: true,
    });
    return Buffer.from(pdf);
  } finally {
    await browser.close();
  }
}
