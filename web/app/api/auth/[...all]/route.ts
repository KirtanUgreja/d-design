// Better Auth's own routes. This static segment wins over app/api/[...path].
import { toNextJsHandler } from "better-auth/next-js";

import { auth } from "@/lib/auth";

const handler = toNextJsHandler(auth);

// The JWT is for the Python API only, minted server-side by the /api proxy.
// The plugin's /token route would hand one to the browser, so it is closed.
function closed(req: Request): boolean {
  return new URL(req.url).pathname.replace(/\/+$/, "") === "/api/auth/token";
}

export async function GET(req: Request): Promise<Response> {
  if (closed(req)) return Response.json({ error: "Not found." }, { status: 404 });
  return handler.GET(req);
}

export async function POST(req: Request): Promise<Response> {
  if (closed(req)) return Response.json({ error: "Not found." }, { status: 404 });
  return handler.POST(req);
}
