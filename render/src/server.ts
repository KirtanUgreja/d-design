/**
 * render as a service (phase 18) — the documented contract (backend.md):
 * "one endpoint, in a validated Deck plus a DesignFamily, out HTML. No
 * database, no model credentials, no auth."
 *
 * The hosted page is pure S3 bytes; this service only turns a deck into the
 * single-file HTML at publish time. It is the same exporter as the CLI
 * (renderDeckToHtml) — no second implementation.
 */
import { createServer } from 'node:http';

import { renderDeckToHtml } from './export.jsx';
import type { Deck } from '@web/schema/generated/Deck.js';

const PORT = Number(process.env.PORT ?? 8001);

type RenderRequest = {
  deck: Deck;
  images?: Record<string, string>;
  badge?: boolean;
};

const server = createServer((req, res) => {
  if (req.method !== 'POST' || req.url !== '/render') {
    res.writeHead(404).end('not found');
    return;
  }

  const chunks: Buffer[] = [];
  req.on('data', (c) => chunks.push(c as Buffer));
  req.on('end', () => {
    try {
      const body = JSON.parse(Buffer.concat(chunks).toString('utf8')) as RenderRequest;
      const html = renderDeckToHtml({
        deck: body.deck,
        images: body.images,
        badge: body.badge ?? true,
      });
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
      res.end(html);
    } catch (err) {
      res.writeHead(400, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: (err as Error).message }));
    }
  });
});

server.listen(PORT, () => {
  console.log(`render service listening on ${PORT}`);
});
