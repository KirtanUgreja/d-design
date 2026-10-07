import { LiveDeck } from "@/components/live-deck";

// A live deck, built by the API and the worker (phase 27). Recorded decks keep
// their own routes under /deck/[id].
export default async function LiveDeckPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <LiveDeck id={id} />;
}
