import { Editor } from "@/components/editor";
import { StepBar } from "@/components/step-bar";
import { getDeck, type DeckParams } from "@/lib/deck";

export default async function EditPage(props: DeckParams) {
  const deck = await getDeck(props);
  return (
    <>
      <StepBar deckId={deck.id} current="deck" />
      <Editor deck={deck} />
    </>
  );
}
