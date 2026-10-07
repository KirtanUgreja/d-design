// The live API (api/app.py), reached through Next's /api rewrite. Every
// response is external input: parsed once, here, into the shapes the screens
// already render (lib/types.ts), and typed from then on. Types come from the
// API's OpenAPI (schema.d.ts, `pnpm api:types`); ponytail: the runtime check is
// hand-written over the fields we read — a generated validator replaces it
// when the API grows (docs/v4/plan/27-app-create-flow.md -> Verify externally).
import type { components } from "@/lib/api/schema";
import { err, ok, type Result } from "@/lib/result";
import type { Fact, Plan, Provenance, Question } from "@/lib/types";

type DeckOut = components["schemas"]["DeckOut"];
export type Status = DeckOut["deck"]["status"];

export interface LiveSlide {
  id: string;
  status: string;
}

export interface LiveDeck {
  id: string;
  version: number;
  status: Status;
  error: string;
  prompt: string;
  thesis: string;
  questions: Question[];
  outline: Plan[];
  facts: Fact[];
  slides: LiveSlide[];
  pending: string[];
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const text = (v: unknown): string => (typeof v === "string" ? v : "");
const STATUSES: readonly Status[] = ["brief", "interview", "outline", "approve", "building", "ready", "error", "aborted"];
const provenance = (v: unknown): Provenance => (v === "YOU" || v === "WEB" ? v : "AI");

function parseDeck(raw: unknown): LiveDeck | null {
  if (!isObj(raw) || !isObj(raw.deck)) return null;
  const d = raw.deck;
  const status = STATUSES.find((s) => s === d.status);
  if (!status || typeof d.id !== "string" || typeof d.version !== "number" || !isObj(d.brief)) return null;
  const story = isObj(d.storyline) ? d.storyline : null;
  return {
    id: d.id,
    version: d.version,
    status,
    error: text(d.error),
    prompt: text(d.brief.prompt),
    thesis: story ? text(story.governing_thought) : "",
    questions: list(raw.questions)
      .filter(isObj)
      .map((q) => ({ fills: text(q.fills), question: text(q.question), suggestions: list(q.suggestions).map(text) })),
    outline: (story ? list(story.slides) : []).filter(isObj).map((s) => ({
      id: text(s.id),
      beat: text(s.beat),
      intent: text(s.intent),
      notes: text(s.notes),
      hasChart: isObj(s.chart),
      provenance: Object.fromEntries(Object.entries(isObj(s.provenance) ? s.provenance : {}).map(([k, v]) => [k, provenance(v)])),
      fields: list(s.fields)
        .filter(isObj)
        .map((f) => ({ name: text(f.name), text: text(f.text), factIds: list(f.fact_ids).map(text) })),
    })),
    facts: list(d.facts)
      .filter(isObj)
      .map((f) => {
        const c = isObj(f.citation) ? f.citation : null;
        return {
          id: text(f.id),
          text: text(f.text),
          value: typeof f.value === "string" ? f.value : null,
          source: f.source === "cited" || f.source === "illustrative" ? f.source : "user",
          status: f.status === "proposed" || f.status === "rejected" ? f.status : "approved",
          asOf: text(f.as_of),
          flags: list(f.flags).map(text),
          citation: c ? { url: text(c.url), title: text(c.title), publisher: text(c.publisher), quote: text(c.snippet) } : null,
        };
      }),
    slides: list(d.slides)
      .filter(isObj)
      .map((s) => ({ id: text(s.id), status: isObj(s.qa) ? text(s.qa.status) : "" })),
    pending: list(raw.pending).map(text),
  };
}

const UNREACHABLE = "We can't reach the deck service. Is it running?";

async function call(path: string, init?: RequestInit): Promise<Result<LiveDeck>> {
  let res: Response;
  try {
    res = await fetch(path, { ...init, headers: { "content-type": "application/json", ...init?.headers } });
  } catch {
    return err(UNREACHABLE);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) {
    if (isObj(body) && typeof body.error === "string") return err(body.error);
    // The API answers every error in JSON; anything else came from in between
    // (the proxy, a server page), which means it was never reached.
    return err(UNREACHABLE);
  }
  const deck = parseDeck(body);
  return deck ? ok(deck) : err("The deck service sent something we couldn't read.");
}

export const api = {
  create: (prompt: string) => call("/api/decks", { method: "POST", body: JSON.stringify({ prompt }) }),
  read: (id: string) => call(`/api/decks/${id}`),
  answer: (id: string, answers: string[], skip: boolean) =>
    call(`/api/decks/${id}/interview`, { method: "POST", body: JSON.stringify({ answers, skip }) }),
  decide: (id: string, version: number, decisions: Record<string, "approved" | "rejected">, order?: string[]) =>
    call(`/api/decks/${id}/outline`, { method: "PATCH", body: JSON.stringify({ version, decisions, order }) }),
  build: (id: string) => call(`/api/decks/${id}/build`, { method: "POST" }),
  abort: (id: string) => call(`/api/decks/${id}/build/abort`, { method: "POST" }),
  thumb: (id: string, slide: string) => `/api/decks/${id}/slides/${slide}/thumb.png`,
  exportUrl: (id: string, kind: "present" | "send" | "pdf") =>
    kind === "pdf" ? `/api/decks/${id}/export.pdf` : `/api/decks/${id}/export.html?flavour=${kind}`,
};

export interface LiveEvent {
  seq: number;
  type: string;
  slideId: string | null;
  status: string | null;
  message: string | null;
}

export function parseEvent(raw: string): LiveEvent | null {
  let v: unknown;
  try {
    v = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isObj(v) || typeof v.seq !== "number" || typeof v.type !== "string") return null;
  return {
    seq: v.seq,
    type: v.type,
    slideId: typeof v.slide_id === "string" ? v.slide_id : null,
    status: typeof v.status === "string" ? v.status : null,
    message: typeof v.message === "string" ? v.message : null,
  };
}
