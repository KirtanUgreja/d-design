// Recorded runs (api/benchtools/record.py), the prototype's only data until
// phase 27 wires the API. A recording is external input: it is parsed once,
// here, and typed from then on (docs/coderules/typescript.md).
// ponytail: hand-written guards over the fields the prototype reads. Phase 27
// replaces this with types generated from the API's OpenAPI and its validator.
import "server-only";

import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

import { err, ok, type Result } from "@/lib/result";

export type Provenance = "YOU" | "AI" | "WEB";

export interface Field {
  name: string;
  text: string;
  factIds: string[];
}

export interface Plan {
  id: string;
  beat: string;
  intent: string;
  fields: Field[];
  provenance: Record<string, Provenance>;
  notes: string;
  hasChart: boolean;
}

export interface Fact {
  id: string;
  text: string;
  value: string | null;
  source: "user" | "cited" | "illustrative";
  status: "proposed" | "approved" | "rejected";
  asOf: string;
  flags: string[];
  citation: { url: string; title: string; publisher: string; quote: string } | null;
}

export interface Question {
  fills: string;
  question: string;
  suggestions: string[];
}

export interface Look {
  id: string;
  pairing: string;
  palette: string;
  grid: string;
  motif: string;
  tiles: string[];
  fonts: string[];
}

export interface DeckEvent {
  type: string;
  t: number;
  slideId: string | null;
  status: string | null;
}

export interface SlideShot {
  id: string;
  thumb: string;
  status: string;
  origin: string;
}

export interface Recording {
  id: string;
  prompt: string;
  audience: string;
  ask: string;
  deckType: string;
  thesis: string;
  questions: Question[];
  outline: Plan[];
  facts: Fact[];
  looks: Look[];
  chosen: string;
  events: DeckEvent[];
  slides: SlideShot[];
  proposal: { slideId: string; instruction: string; after: string } | null;
  exports: { present: string; send: string; pdf: string };
}

const ROOT = path.join(process.cwd(), "public", "fixtures");

// --- narrowing helpers --------------------------------------------------------

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const str = (o: Obj, k: string): string => {
  const v = o[k];
  if (typeof v !== "string") throw new Error(`fixture: ${k} is not a string`);
  return v;
};
const optStr = (o: Obj, k: string): string | null => (typeof o[k] === "string" ? (o[k] as string) : null);
const arr = (o: Obj, k: string): unknown[] => {
  const v = o[k];
  if (!Array.isArray(v)) throw new Error(`fixture: ${k} is not a list`);
  return v;
};
const obj = (v: unknown, what: string): Obj => {
  if (!isObj(v)) throw new Error(`fixture: ${what} is not an object`);
  return v;
};
const strings = (o: Obj, k: string): string[] => arr(o, k).filter((v): v is string => typeof v === "string");
const provenance = (v: unknown): Provenance => (v === "YOU" || v === "WEB" ? v : "AI");

function parse(id: string, raw: unknown): Recording {
  const m = obj(raw, "manifest");
  const brief = obj(m.brief, "brief");
  const outline = obj(m.outline, "outline");
  return {
    id,
    prompt: str(brief, "prompt"),
    audience: str(brief, "audience"),
    ask: str(brief, "ask"),
    deckType: str(brief, "deck_type"),
    thesis: str(outline, "governing_thought"),
    questions: arr(m, "questions").map((q) => {
      const o = obj(q, "question");
      return { fills: str(o, "fills"), question: str(o, "question"), suggestions: strings(o, "suggestions") };
    }),
    outline: arr(outline, "slides").map((s) => {
      const o = obj(s, "slide");
      const prov = isObj(o.provenance) ? o.provenance : {};
      return {
        id: str(o, "id"),
        beat: str(o, "beat"),
        intent: str(o, "intent"),
        notes: typeof o.notes === "string" ? o.notes : "",
        hasChart: isObj(o.chart),
        provenance: Object.fromEntries(Object.entries(prov).map(([k, v]) => [k, provenance(v)])),
        fields: arr(o, "fields").map((f) => {
          const fo = obj(f, "field");
          return { name: str(fo, "name"), text: str(fo, "text"), factIds: strings(fo, "fact_ids") };
        }),
      };
    }),
    facts: arr(m, "facts").map((f) => {
      const o = obj(f, "fact");
      const c = isObj(o.citation) ? o.citation : null;
      const source = o.source === "cited" || o.source === "illustrative" ? o.source : "user";
      const status = o.status === "proposed" || o.status === "rejected" ? o.status : "approved";
      return {
        id: str(o, "id"),
        text: str(o, "text"),
        value: optStr(o, "value"),
        source,
        status,
        asOf: optStr(o, "as_of") ?? "",
        flags: strings(o, "flags"),
        citation: c
          ? { url: str(c, "url"), title: str(c, "title"), publisher: optStr(c, "publisher") ?? "", quote: str(c, "snippet") }
          : null,
      };
    }),
    looks: arr(m, "looks").map((l) => {
      const o = obj(l, "look");
      const look = obj(o.look, "look axes");
      return {
        id: str(o, "id"),
        pairing: str(look, "pairing"),
        palette: str(look, "palette"),
        grid: str(look, "grid"),
        motif: str(look, "motif"),
        tiles: strings(o, "tiles"),
        fonts: strings(o, "fonts"),
      };
    }),
    chosen: str(m, "chosen"),
    events: arr(m, "events").map((e) => {
      const o = obj(e, "event");
      const t = o.t;
      return {
        type: str(o, "type"),
        t: typeof t === "number" ? t : 0,
        slideId: optStr(o, "slide_id"),
        status: optStr(o, "status"),
      };
    }),
    slides: arr(m, "slides").map((s) => {
      const o = obj(s, "slide shot");
      return { id: str(o, "id"), thumb: str(o, "thumb"), status: str(o, "status"), origin: str(o, "origin") };
    }),
    proposal: isObj(m.proposal)
      ? { slideId: str(m.proposal, "slide_id"), instruction: str(m.proposal, "instruction"), after: str(m.proposal, "after") }
      : null,
    exports: (() => {
      const e = obj(m.exports, "exports");
      return { present: str(e, "present"), send: str(e, "send"), pdf: str(e, "pdf") };
    })(),
  };
}

export async function recordingIds(): Promise<string[]> {
  const entries = await readdir(ROOT, { withFileTypes: true });
  return entries.filter((e) => e.isDirectory()).map((e) => e.name).sort();
}

/** One recording, parsed. An unknown id is an expected miss, not a bug. */
export async function loadRecording(id: string): Promise<Result<Recording, "not_found">> {
  if (!(await recordingIds()).includes(id)) return err("not_found");
  const raw: unknown = JSON.parse(await readFile(path.join(ROOT, id, "manifest.json"), "utf8"));
  return ok(parse(id, raw));
}

/** A path under /fixtures/<id>/ for the browser. */
export const asset = (id: string, file: string): string => `/fixtures/${id}/${file}`;
