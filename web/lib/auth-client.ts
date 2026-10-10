"use client";
// Better Auth in the browser: sign up, sign in, sign out, the session, the
// account. No JWT client plugin on purpose — the browser never holds a token.
import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient();
