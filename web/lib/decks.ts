// The signed-in person's decks: GET /api/decks through the /api proxy, so only
// theirs. Parsed once here into what the cards show (newest first: the API
// already orders them).
import { err, ok, type Result } from "@/lib/result";

export interface DeckRow {
  id: string;
  title: string;
  status: string;
  version: number;
  slides: number; // in its outline
  cover: string | null; // the first slide's id, once the deck is built
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): string => (typeof v === "string" ? v : "");

export const STATUS_LABEL: Record<string, string> = {
  brief: "Reading the brief",
  interview: "Questions waiting",
  outline: "Writing the outline",
  approve: "Outline to approve",
  building: "Building",
  ready: "Ready",
  error: "Stopped",
  aborted: "Stopped",
};

function row(v: unknown): DeckRow | null {
  if (!isObj(v) || typeof v.id !== "string") return null;
  const story = isObj(v.storyline) ? v.storyline : {};
  const brief = isObj(v.brief) ? v.brief : {};
  const plans = Array.isArray(story.slides) ? story.slides.filter(isObj) : [];
  const status = text(v.status);
  const built = status === "ready" || status === "aborted";
  return {
    id: v.id,
    title: text(story.governing_thought) || text(v.title) || text(brief.prompt) || "Untitled deck",
    status,
    version: typeof v.version === "number" ? v.version : 0,
    slides: plans.length,
    cover: built && plans[0] ? text(plans[0].id) || null : null,
  };
}

/** null: signed out (the caller shows nothing); otherwise the decks or why not. */
export async function loadDecks(): Promise<Result<DeckRow[]> | null> {
  let res: Response;
  try {
    res = await fetch("/api/decks", { headers: { accept: "application/json" } });
  } catch {
    return err("We can't reach the deck service right now.");
  }
  if (res.status === 401) return null;
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) return err(isObj(body) && typeof body.error === "string" ? body.error : "We can't reach the deck service.");
  if (!Array.isArray(body)) return err("The deck service sent something we couldn't read.");
  return ok(body.map(row).filter((r): r is DeckRow => r !== null));
}
