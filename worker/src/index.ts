/**
 * The upload worker — the isolated process (security/README.md trust
 * boundaries: "the process that parses hostile bytes has nothing worth
 * stealing").
 *
 * This service has NO database access, NO sessions, NO VPC route, and no
 * secret beyond what it needs to serve one job: verify + re-encode + sanitize
 * an uploaded brand asset and hand the safe bytes back. web forwards the file
 * here; the worker never persists it itself.
 */
import { createServer } from "node:http";

import { processUpload, UploadRejected } from "./process.js";

const PORT = Number(process.env.PORT ?? 8080);

const server = createServer(async (req, res) => {
  if (req.method !== "POST" || req.url !== "/process") {
    res.writeHead(404).end("not found");
    return;
  }

  const claimedType = req.headers["content-type"] ?? "";
  const chunks: Buffer[] = [];

  try {
    for await (const chunk of req) {
      chunks.push(chunk as Buffer);
    }
    const bytes = Buffer.concat(chunks);
    const result = await processUpload(bytes, claimedType);

    res.writeHead(200, { "content-type": "application/json" });
    res.end(
      JSON.stringify({
        ok: true,
        contentType: result.contentType,
        size: result.bytes.length,
        dominantColor: result.dominantColor ?? null,
        data: result.bytes.toString("base64"),
      }),
    );
  } catch (err) {
    const message =
      err instanceof UploadRejected ? err.message : "processing failed";
    res.writeHead(422, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: false, error: message }));
  }
});

server.listen(PORT, () => {
  console.log(`upload worker listening on ${PORT}`);
});
