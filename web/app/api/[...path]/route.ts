// The one door to the Python API (replaces next.config's rewrite, phase 29).
// No session: 401 here, and the API is never called. A session: a fresh
// short-lived JWT from Better Auth goes upstream as a Bearer token, so the
// browser never sees it. The response body is passed through as a stream,
// unbuffered, so the deck's event stream (SSE) arrives as it is written.
import type { NextRequest } from "next/server";

import { tokenFor } from "@/lib/auth";

export const dynamic = "force-dynamic";

const API = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

// Only what the API reads goes up; cookies stay here.
const UP = ["accept", "content-type", "last-event-id", "if-none-match", "if-modified-since", "range"];
// Only what the browser needs comes back. No content-encoding or length:
// fetch has already decoded the body, so those would lie.
const DOWN = ["content-type", "cache-control", "content-disposition", "etag", "last-modified", "location", "retry-after", "vary"];

const fail = (status: number, error: string) => Response.json({ error }, { status, headers: { "cache-control": "no-store" } });

async function forward(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }): Promise<Response> {
  let token: string | null;
  try {
    token = await tokenFor(req.headers);
  } catch {
    // A session check that throws refuses (AGENTS.md rule 10).
    return fail(401, "Sign in to continue.");
  }
  if (!token) return fail(401, "Sign in to continue.");

  const { path } = await ctx.params;
  // Dot segments would let a path climb out of the API's /api prefix.
  if (path.some((p) => p === "." || p === "..")) return fail(404, "Not found.");
  const target = new URL(`/api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`, API);
  const headers = new Headers({ authorization: `Bearer ${token}` });
  for (const name of UP) {
    const value = req.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  let res: Response;
  try {
    res = await fetch(target, {
      method: req.method,
      headers,
      // ponytail: request bodies are buffered (small JSON today); stream them
      // with `duplex: "half"` when uploads grow past a few MB.
      body: hasBody ? await req.arrayBuffer() : undefined,
      redirect: "manual",
      cache: "no-store",
      signal: req.signal,
    });
  } catch {
    return fail(502, "We can't reach the deck service. Is it running?");
  }

  const out = new Headers();
  for (const name of DOWN) {
    const value = res.headers.get(name);
    if (value !== null) out.set(name, value);
  }
  if (out.get("content-type")?.startsWith("text/event-stream")) {
    out.set("cache-control", "no-cache, no-transform");
    out.set("x-accel-buffering", "no");
  }
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: out });
}

export { forward as DELETE, forward as GET, forward as HEAD, forward as OPTIONS, forward as PATCH, forward as POST, forward as PUT };
