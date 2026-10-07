// The deck's content as every screen reads it, whether it came from a
// recording (lib/fixtures.ts) or the live API (lib/api/client.ts).
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

