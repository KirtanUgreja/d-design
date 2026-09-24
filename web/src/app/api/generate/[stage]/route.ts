/**
 * The generation route — web's proxy to the pipeline (v3).
 *
 * The editor cannot call api directly: the session cookie is httpOnly and api
 * is not exposed to the browser. So the browser posts here, this route
 * resolves the session and forwards, and api's answer comes back parsed.
 *
 * The stage is a path segment (`/api/generate/interview`) rather than a field
 * in the body, so each stage keeps its own payload schema in its own branch —
 * exact types, no polymorphic body to discriminate by hand.
 */
import { headers } from 'next/headers';
import { NextResponse } from 'next/server';

import {
  generateBuild,
  generateInterview,
  generateMapping,
  type GenerationRefusal,
} from '../../../../features/generation/generation.data.js';
import {
  BriefSchema,
  BuildInSchema,
  MappingInSchema,
  StageSchema,
} from '../../../../features/generation/index.js';
import { auth } from '../../../../lib/auth.js';
import type { Result } from '../../../../lib/result.js';

export const dynamic = 'force-dynamic';

/** The status an expected refusal maps to. A model stage that failed after its
 * repair is an upstream failure (502); an unreachable service is 503. */
function statusFor(kind: GenerationRefusal['kind']): number {
  switch (kind) {
    case 'unauthorized':
      return 401;
    case 'upstream':
      return 502;
    case 'unreachable':
      return 503;
  }
}

function forward(result: Result<unknown, GenerationRefusal>): NextResponse {
  if (!result.ok) {
    return NextResponse.json(
      { error: result.error.message },
      { status: statusFor(result.error.kind) },
    );
  }
  return NextResponse.json(result.value, { status: 200 });
}

function badRequest(what: string): NextResponse {
  return NextResponse.json({ error: `invalid ${what}` }, { status: 400 });
}

export async function POST(req: Request, ctx: { params: Promise<{ stage: string }> }) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 });
  }

  const parsedStage = StageSchema.safeParse((await ctx.params).stage);
  if (!parsedStage.success) {
    return NextResponse.json({ error: 'unknown stage' }, { status: 404 });
  }

  // One parse at the boundary — the browser's body is external input.
  const body: unknown = await req.json().catch(() => null);

  switch (parsedStage.data) {
    case 'interview': {
      const parsed = BriefSchema.safeParse(body);
      return parsed.success ? forward(await generateInterview(parsed.data)) : badRequest('brief');
    }
    case 'mapping': {
      const parsed = MappingInSchema.safeParse(body);
      return parsed.success ? forward(await generateMapping(parsed.data)) : badRequest('outline');
    }
    case 'build': {
      const parsed = BuildInSchema.safeParse(body);
      return parsed.success ? forward(await generateBuild(parsed.data.deck)) : badRequest('deck');
    }
  }
}
