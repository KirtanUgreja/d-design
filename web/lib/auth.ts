// Better Auth, server side (phase 29, master plan A2). Email and password only:
// no OAuth, no email verification, no reset. Its tables live in their own
// Postgres database (AUTH_DATABASE_URL), created by its CLI:
//   pnpm dlx auth@1.7.7 migrate --config lib/auth.ts --yes
// Python never reads these tables. It learns who you are from the JWT this
// plugin signs, which the /api proxy mints per request and the browser never
// sees (docs/security/tenancy-and-data.md -> Authentication).
//
// Not marked server-only: the CLI imports this file outside Next. Only route
// handlers, server components and the proxy import it.
import { betterAuth } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { nextCookies } from "better-auth/next-js";
import { jwt } from "better-auth/plugins";
import { Pool } from "pg";

import { isAllowedEmail } from "@/lib/auth-allow";

const BASE_URL = process.env.BETTER_AUTH_URL ?? "http://localhost:3000";
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

/** What FastAPI checks (api side, PyJWKClient against `${BASE_URL}/api/auth/jwks`). */
export const JWT_ISSUER = BASE_URL;
export const JWT_AUDIENCE = "d-design-api";

const NOT_ALLOWED = "This email isn't on the list for this preview. Ask the owner to add it.";

function refuseUnlisted(email: unknown): void {
  if (!isAllowedEmail(email, process.env.ALLOWED_EMAILS)) throw new APIError("FORBIDDEN", { message: NOT_ALLOWED });
}

// Deleting an account deletes its decks and files in the Python API first; if
// that fails, the account stays (a person can retry; orphaned decks cannot).
// Bound after `auth` exists, because the token comes from auth itself.
let purgeDecks: ((headers: Headers) => Promise<void>) | null = null;

export const auth = betterAuth({
  baseURL: BASE_URL,
  database: new Pool({ connectionString: process.env.AUTH_DATABASE_URL, max: 5 }),
  emailAndPassword: { enabled: true, autoSignIn: true, minPasswordLength: 10 },
  user: {
    deleteUser: {
      enabled: true,
      beforeDelete: async (_user, request) => {
        if (!request || !purgeDecks) throw new APIError("BAD_REQUEST", { message: "Delete your account from the account page." });
        await purgeDecks(request.headers);
      },
    },
  },
  // Server-side, so the client cannot skip it: the sign-up route checks the
  // list before anything else, and the user-create hook checks again, so no
  // other path that creates a user gets past it either.
  hooks: {
    before: createAuthMiddleware(async (ctx) => {
      if (ctx.path === "/sign-up/email") refuseUnlisted(ctx.body?.email);
    }),
  },
  databaseHooks: {
    user: {
      create: {
        before: async (user) => {
          refuseUnlisted(user.email);
        },
      },
    },
  },
  plugins: [
    jwt({
      // The browser never gets a JWT: no set-auth-jwt header on get-session, and
      // the /token route is refused in app/api/auth/[...all]/route.ts.
      disableSettingJwtHeader: true,
      jwks: { keyPairConfig: { alg: "EdDSA", crv: "Ed25519" } },
      jwt: {
        issuer: JWT_ISSUER,
        audience: JWT_AUDIENCE,
        // Minted fresh for every proxied request, so it can be short.
        expirationTime: "5m",
        definePayload: ({ user }) => ({ email: user.email, name: user.name }),
      },
    }),
    nextCookies(), // last, per the docs: lets server actions set the cookie
  ],
});

/** A short-lived JWT for the signed-in user of these request headers, or null when there is no session. */
export async function tokenFor(headers: Headers): Promise<string | null> {
  const session = await auth.api.getSession({ headers });
  if (!session) return null;
  const { token } = await auth.api.getToken({ headers });
  return token;
}

purgeDecks = async (headers) => {
  const token = await tokenFor(headers);
  if (!token) throw new APIError("UNAUTHORIZED");
  let res: Response;
  try {
    res = await fetch(new URL("/api/me", API_ORIGIN), { method: "DELETE", headers: { authorization: `Bearer ${token}` } });
  } catch {
    throw new APIError("SERVICE_UNAVAILABLE", { message: "We couldn't delete your decks. Nothing was deleted; try again." });
  }
  if (!res.ok && res.status !== 404) {
    throw new APIError("SERVICE_UNAVAILABLE", { message: "We couldn't delete your decks. Nothing was deleted; try again." });
  }
};
