// Every state nobody designs, in final copy (docs/design/app.md -> "The states
// nobody designs"). In the prototype they are reached from here; phase 27
// reaches them from real failures. Never a raw exception.
import Link from "next/link";

const STATES: { name: string; copy: string; action: string }[] = [
  { name: "The model refused", copy: "That request can't be written as a slide. Try saying what the slide should show instead.", action: "Rewrite the request" },
  { name: "Generation failed", copy: "We stopped at slide 6 of 10. The five finished slides, your brief and your outline are saved.", action: "Continue from slide 6" },
  { name: "Connection dropped during the watch", copy: "(Nothing shown.) The build keeps going on our side; this page catches up when it reconnects.", action: "—" },
  { name: "A slide needs attention", copy: "The headline runs off the right edge on slide 4.", action: "Fit to slide · Different layout" },
  { name: "An edit broke the slide", copy: "Your new text is longer than the space for it. It's kept — choose how to fit it.", action: "Fit to slide · Undo" },
  { name: "An AI change failed", copy: "That change didn't work, so the slide is as it was.", action: "Try again" },
  { name: "A look change broke slides", copy: "The new look is on. Two slides were refitted automatically; one needs a look from you.", action: "Show me · Undo the look" },
  { name: "Research found nothing citable", copy: "We found no source we trust for this claim. It stays marked until you add a source, keep it as illustrative, or cut it.", action: "Add a source · Keep · Cut" },
  { name: "An image failed", copy: "Slide 3 is composed without its image.", action: "Add image" },
  { name: "Budget used up (phase 29)", copy: "You've used this month's generations. Editing, presenting and exporting still work. New decks resume on 1 November.", action: "See plans" },
  { name: "Offline", copy: "You're offline. Your changes are kept here and saved when you're back.", action: "—" },
  { name: "No decks yet", copy: "What are you presenting?", action: "The prompt box" },
];

export default function StatesPage() {
  return (
    <main className="mx-auto max-w-4xl px-8 py-10">
      <Link href="/" className="font-display text-lg">
        d-design
      </Link>
      <h1 className="mt-6 font-display text-3xl">The states nobody designs</h1>
      <p className="mt-2 text-sm text-ink-2">Every failure a person can meet, in the words they will see, with one next step.</p>
      <table className="mt-8 w-full border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-ink">
            <th className="py-2 pr-4 font-medium">State</th>
            <th className="py-2 pr-4 font-medium">What they read</th>
            <th className="py-2 font-medium">What they can do</th>
          </tr>
        </thead>
        <tbody>
          {STATES.map((s) => (
            <tr key={s.name} className="border-b border-rule align-top">
              <td className="py-3 pr-4 text-ink-2">{s.name}</td>
              <td className="py-3 pr-4">{s.copy}</td>
              <td className="py-3">{s.action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
