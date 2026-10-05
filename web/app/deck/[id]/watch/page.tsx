import { StepBar } from "@/components/step-bar";
import { Watch } from "@/components/watch";
import { getDeck, type DeckParams } from "@/lib/deck";

export default async function WatchPage(props: DeckParams) {
  const deck = await getDeck(props);
  return (
    <>
      <StepBar deckId={deck.id} current="deck" />
      <Watch deck={deck} />
    </>
  );
}
