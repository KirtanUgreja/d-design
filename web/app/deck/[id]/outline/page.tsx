import { OutlineGate } from "@/components/outline-gate";
import { StepBar } from "@/components/step-bar";
import { getDeck, type DeckParams } from "@/lib/deck";

export default async function OutlinePage(props: DeckParams) {
  const deck = await getDeck(props);
  return (
    <>
      <StepBar deckId={deck.id} current="outline" />
      <OutlineGate deck={deck} />
    </>
  );
}
