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
  title: string; // the deck's short name, once the outline exists
  thesis: string;
  questions: Question[];
  outline: Plan[];
  facts: Fact[];
  slides: LiveSlide[];
  pending: string[];
  logo: "none" | "cover" | "ends" | "all";
  logoNote: string;
  logoColour: string; // the logo's main colour, offered as the brand colour
  brand: string[]; // the user's brand colours, as #rrggbb; empty = generated
  screens: { caption: string; ready: boolean; note: string }[]; // the person's own screenshots
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const text = (v: unknown): string => (typeof v === "string" ? v : "");
const STATUSES: readonly Status[] = ["brief", "interview", "outline", "approve", "building", "ready", "error", "aborted"];
const HEX = /^#[0-9a-f]{6}$/i;
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
    title: story ? text(story.title) : "",
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
    logo: d.logo === "cover" || d.logo === "ends" || d.logo === "all" ? d.logo : "none",
    logoNote: text(d.logo_note),
    logoColour: HEX.test(text(d.logo_colour)) ? text(d.logo_colour) : "",
    brand: (isObj(d.brief.brand) ? list(d.brief.brand.colors) : []).map(text).filter((c) => HEX.test(c)),
    screens: list(d.screens)
      .filter(isObj)
      .map((s) => ({ caption: text(s.caption), ready: s.ready === true, note: text(s.note) })),
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

// The outcome of the last edit, numbered by its event so a repeat still counts.
export interface Notice {
  text: string;
  seq: number;
  proposal?: string; // a slide id: a change asked in words is ready to compare
}

export interface History {
  labels: string[];
  at: number;
}

async function history(path: string, init?: RequestInit): Promise<Result<History>> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    return err(UNREACHABLE);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) return err(isObj(body) && typeof body.error === "string" ? body.error : UNREACHABLE);
  if (!isObj(body) || typeof body.at !== "number") return err("The deck service sent something we couldn't read.");
  return ok({ labels: list(body.labels).map(text), at: body.at });
}

// The deck's one generated style (phase 39): shown at the outline gate.
export interface StyleCard {
  language: string;
  name: string;
  idea: string;
  display: string;
  text: string;
  colors: Record<string, string>;
  imageStyle: string;
  previews: string[];
}

async function styleCard(path: string): Promise<Result<StyleCard>> {
  let res: Response;
  try {
    res = await fetch(path);
  } catch {
    return err(UNREACHABLE);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) return err(isObj(body) && typeof body.error === "string" ? body.error : UNREACHABLE);
  if (!isObj(body) || typeof body.language !== "string") return err("The deck service sent something we couldn't read.");
  const colors = isObj(body.colors) ? body.colors : {};
  return ok({
    language: body.language,
    name: text(body.name),
    idea: text(body.idea),
    display: text(body.display),
    text: text(body.text),
    // Only plain hex reaches a style attribute.
    colors: Object.fromEntries(Object.entries(colors).filter((e): e is [string, string] => typeof e[1] === "string" && HEX.test(e[1]))),
    imageStyle: text(body.image_style),
    // Named by the look (preview-<look>-<n>.png), so Another style never shows the last one.
    previews: list(body.previews).map(text).filter((n) => /^preview-\d+-[1-3]\.png$/.test(n)),
  });
}

// What the composer may say about a new deck besides its brief; the API
// fills in its own defaults for anything left out.
export type DeckKind = "auto" | "pitch" | "sales" | "launch" | "investor_update" | "partnership" | "project";
export type DeckTone = "plain" | "confident" | "warm" | "bold";
export interface NewDeckOptions {
  kind?: DeckKind;
  tone?: DeckTone;
  slides?: number;
}

// 204 on success; the API's own words on a refusal.
async function deleteDeck(id: string): Promise<Result<null>> {
  let res: Response;
  try {
    res = await fetch(`/api/decks/${id}`, { method: "DELETE" });
  } catch {
    return err(UNREACHABLE);
  }
  if (res.ok) return ok(null);
  const body: unknown = await res.json().catch(() => null);
  return err(isObj(body) && typeof body.error === "string" ? body.error : UNREACHABLE);
}

export const api = {
  deleteDeck,
  style: (id: string) => styleCard(`/api/decks/${id}/style`),
  anotherStyle: (id: string) => call(`/api/decks/${id}/style`, { method: "POST" }),
  setBrand: (id: string, colors: string[]) =>
    call(`/api/decks/${id}/brand`, { method: "PUT", body: JSON.stringify({ colors }) }),
  styleThumb: (id: string, name: string, version: number) => `/api/decks/${id}/style/${name}?v=${version}`,
  create: (prompt: string, options: NewDeckOptions = {}) =>
    call("/api/decks", {
      method: "POST",
      body: JSON.stringify({
        prompt,
        ...(options.kind ? { deck_type: options.kind } : {}),
        ...(options.tone ? { tone: options.tone } : {}),
        ...(options.slides ? { slide_count: options.slides } : {}),
      }),
    }),
  read: (id: string) => call(`/api/decks/${id}`),
  answer: (id: string, answers: string[], skip: boolean) =>
    call(`/api/decks/${id}/interview`, { method: "POST", body: JSON.stringify({ answers, skip }) }),
  decide: (id: string, version: number, decisions: Record<string, "approved" | "rejected">, order?: string[]) =>
    call(`/api/decks/${id}/outline`, { method: "PATCH", body: JSON.stringify({ version, decisions, order }) }),
  // The person's own words for an outline's fields, and slides to drop, saved
  // with the order and decisions made so far.
  editOutline: (
    id: string,
    version: number,
    edit: {
      words?: Record<string, Record<string, string>>;
      remove?: string[];
      order?: string[];
      decisions?: Record<string, "approved" | "rejected">;
    },
  ) => call(`/api/decks/${id}/outline`, { method: "PATCH", body: JSON.stringify({ version, ...edit }) }),
  rewriteOutline: (id: string, instruction: string) =>
    call(`/api/decks/${id}/outline/ask`, { method: "POST", body: JSON.stringify({ instruction }) }),
  rename: (id: string, title: string) => call(`/api/decks/${id}/title`, { method: "PUT", body: JSON.stringify({ title }) }),
  build: (id: string) => call(`/api/decks/${id}/build`, { method: "POST" }),
  retry: (id: string) => call(`/api/decks/${id}/retry`, { method: "POST" }),
  abort: (id: string) => call(`/api/decks/${id}/build/abort`, { method: "POST" }),
  // The version busts the cache: an edit re-renders the screenshot in place.
  thumb: (id: string, slide: string, version = 0) => `/api/decks/${id}/slides/${slide}/thumb.png?v=${version}`,
  editText: (id: string, slide: string, field: string, text: string) =>
    call(`/api/decks/${id}/slides/${slide}/fields`, { method: "PATCH", body: JSON.stringify({ field, text }) }),
  reorder: (id: string, slides: string[]) => call(`/api/decks/${id}/reorder`, { method: "POST", body: JSON.stringify({ slides }) }),
  remove: (id: string, slide: string) => call(`/api/decks/${id}/slides/${slide}`, { method: "DELETE" }),
  recolour: (id: string) => call(`/api/decks/${id}/recolour`, { method: "POST" }),
  uploadLogo: (id: string, data: string) =>
    call(`/api/decks/${id}/logo`, { method: "PUT", body: JSON.stringify({ data, placement: "ends" }) }),
  removeLogo: (id: string) => call(`/api/decks/${id}/logo`, { method: "DELETE" }),
  addScreen: (id: string, data: string, caption: string) =>
    call(`/api/decks/${id}/screens`, { method: "POST", body: JSON.stringify({ data, caption }) }),
  removeScreen: (id: string, n: number) => call(`/api/decks/${id}/screens/${n}`, { method: "DELETE" }),
  screenUrl: (id: string, n: number, v: number) => `/api/decks/${id}/screens/${n}.webp?v=${v}`,
  logoUrl: (id: string, version: number) => `/api/decks/${id}/logo.png?v=${version}`,
  ask: (id: string, slide: string, instruction: string) =>
    call(`/api/decks/${id}/slides/${slide}/ask`, { method: "POST", body: JSON.stringify({ instruction }) }),
  accept: (id: string, slide: string) => call(`/api/decks/${id}/slides/${slide}/accept`, { method: "POST" }),
  askDeck: (id: string, instruction: string) =>
    call(`/api/decks/${id}/ask`, { method: "POST", body: JSON.stringify({ instruction }) }),
  proposalThumb: (id: string, slide: string, seq: number) => `/api/decks/${id}/slides/${slide}/proposal.png?v=${seq}`,
  fit: (id: string, slide: string) => call(`/api/decks/${id}/slides/${slide}/fit`, { method: "POST" }),
  history: (id: string) => history(`/api/decks/${id}/history`),
  undo: (id: string) => history(`/api/decks/${id}/undo`, { method: "POST" }),
  redo: (id: string) => history(`/api/decks/${id}/redo`, { method: "POST" }),
  exportUrl: (id: string, kind: "present" | "send" | "pdf") =>
    kind === "pdf" ? `/api/decks/${id}/export.pdf` : `/api/decks/${id}/export.html?flavour=${kind}`,
};

export interface LiveEvent {
  seq: number;
  type: string;
  slideId: string | null;
  status: string | null;
  message: string | null;
  // The work made visible while waiting (2026-10-10): a slide's step, a
  // stage's name and state, and what research found.
  step: string | null;
  name: string | null;
  state: string | null;
  origin: string | null;
  sources: number | null;
  publishers: string[];
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
    step: typeof v.step === "string" ? v.step : null,
    name: typeof v.name === "string" ? v.name : null,
    state: typeof v.state === "string" ? v.state : null,
    origin: typeof v.origin === "string" ? v.origin : null,
    sources: typeof v.sources === "number" ? v.sources : null,
    publishers: list(v.publishers).filter((x): x is string => typeof x === "string").slice(0, 6),
  };
}
