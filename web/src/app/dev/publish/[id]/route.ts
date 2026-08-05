// Dev-only trigger for `publishExperience` — the editor calls the same
// feature function from a real UI in phase 09; until then, this is how a
// hand-written fixture (created via `POST /experiences` on `api`) gets
// published for manual and e2e verification (docs/v1/plan/05-publish-present-embed.md).

import { publishExperience } from '@/features/publish';

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const result = await publishExperience(id);
  if (!result.ok) {
    return Response.json({ error: result.error }, { status: 502 });
  }
  return Response.json({ published: true });
}
