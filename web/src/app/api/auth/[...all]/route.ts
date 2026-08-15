/**
 * Better Auth's API route — the catch-all that handles signup, login,
 * session, logout, and the rest.
 */
import { toNextJsHandler } from 'better-auth/next-js';

import { auth } from '../../../../lib/auth.js';

export const { GET, POST } = toNextJsHandler(auth);
