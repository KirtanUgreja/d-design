// Dev-only trigger for `unpublishExperience` — see dev/publish/[id]/route.ts.

import { unpublishExperience } from '@/features/publish';

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const result = await unpublishExperience(id);
  if (!result.ok) {
    return Response.json({ error: result.error }, { status: 502 });
  }
  return Response.json({ unpublished: true });
}
