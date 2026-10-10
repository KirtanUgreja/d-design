import { Composer } from "@/components/composer";
import { Proofs } from "@/components/proofs";
import { Showcase } from "@/components/showcase";
import { YourDecks } from "@/components/your-decks";

// Example briefs for the composer's chips: they fill the box, nothing more.
// (The recorded runs of the old engine are gone from here: owner, 2026-10-10.)
const EXAMPLES = [
  {
    id: "voice",
    type: "pitch",
    short: "Voice to app",
    prompt: "Seed pitch for Swarvani, a voice-to-app builder that turns a live product call into a working app, for early-stage investors",
  },
  {
    id: "coffee",
    type: "investor_update",
    short: "Coffee brand",
    prompt: "Q3 investor update for Brewly, a specialty coffee subscription: revenue up 31%, churn down, wholesale delayed to Q1",
  },
  {
    id: "capstone",
    type: "project",
    short: "Capstone",
    prompt: "Final-year project presentation for a campus lost-and-found app: problem, solution, architecture, tech stack and demo",
  },
  {
    id: "launch",
    type: "launch",
    short: "Chess course",
    prompt: "Launch deck for a chess course inside a language-learning app, for press and partners",
  },
];

export default function Home() {
  return (
    <main>
      <section className="mx-auto max-w-[880px] px-4 pt-12 pb-12 sm:px-8 sm:pt-20 sm:pb-16">
        <Composer examples={EXAMPLES} />
      </section>

      <div className="mx-auto max-w-[1440px] px-4 sm:px-8">
        <YourDecks />
      </div>

      <Showcase />
      <Proofs />
    </main>
  );
}
