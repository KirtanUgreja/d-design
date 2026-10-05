import { LookPicker } from "@/components/look-picker";
import { StepBar } from "@/components/step-bar";
import { getDeck, type DeckParams } from "@/lib/deck";

export default async function LookPage(props: DeckParams) {
  const deck = await getDeck(props);
  return (
    <>
      <StepBar deckId={deck.id} current="look" />
      <LookPicker deck={deck} />
    </>
  );
}
