// The signed-in user's profile as the Python API keeps it (master plan A6):
//   GET   /api/me  -> { id, email, name, avatar: {style, seed, options} | null }
//   PATCH /api/me  <- { avatar?: {style, seed, options}, name? }  -> the same shape
// Every response is external input, parsed once here.
import { err, ok, type Result } from "@/lib/result";

/**
 * The styles offered, each drawn in the browser by @dicebear/core from
 * @dicebear/styles. All CC0 1.0 (checked in the package's LICENSE.md,
 * 2026-10-08), so no credit is owed; the account page names them anyway.
 */
export const AVATAR_STYLES = [
  { id: "notionists", label: "Notionists", artist: "Zoish", license: "CC0 1.0" },
  { id: "lorelei", label: "Lorelei", artist: "Lisa Wischofsky", license: "CC0 1.0" },
  { id: "open-peeps", label: "Open Peeps", artist: "Pablo Stanley", license: "CC0 1.0" },
  { id: "thumbs", label: "Thumbs", artist: "DiceBear", license: "CC0 1.0" },
  { id: "shapes", label: "Shapes", artist: "DiceBear", license: "CC0 1.0" },
  { id: "pixel-art", label: "Pixel Art", artist: "DiceBear", license: "CC0 1.0" },
] as const;

export type AvatarStyle = (typeof AVATAR_STYLES)[number]["id"];

/** Backgrounds from our brand (app/globals.css): paper-2, rule, olive, oxide, ink-2. Flat fills only. */
export const AVATAR_BACKGROUNDS = [
  { hex: "#ece7dc", label: "Paper" },
  { hex: "#d6d0c3", label: "Stone" },
  { hex: "#3f5220", label: "Olive" },
  { hex: "#8a3b12", label: "Oxide" },
  { hex: "#5d5a52", label: "Graphite" },
] as const;

export type AvatarBackground = (typeof AVATAR_BACKGROUNDS)[number]["hex"];

export interface AvatarSpec {
  style: AvatarStyle;
  seed: string;
  options: { backgroundColor: AvatarBackground };
}

export interface Me {
  id: string;
  email: string;
  name: string;
  avatar: AvatarSpec | null;
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);

export function parseAvatar(v: unknown): AvatarSpec | null {
  if (!isObj(v) || typeof v.seed !== "string" || !v.seed) return null;
  const style = AVATAR_STYLES.find((s) => s.id === v.style)?.id;
  if (!style) return null;
  const opts = isObj(v.options) ? v.options : {};
  const bg = AVATAR_BACKGROUNDS.find((b) => b.hex === opts.backgroundColor)?.hex ?? AVATAR_BACKGROUNDS[0].hex;
  return { style, seed: v.seed.slice(0, 64), options: { backgroundColor: bg } };
}

function parseMe(v: unknown): Me | null {
  if (!isObj(v) || typeof v.id !== "string" || typeof v.email !== "string") return null;
  return { id: v.id, email: v.email, name: typeof v.name === "string" ? v.name : "", avatar: parseAvatar(v.avatar) };
}

export const newSeed = (): string => crypto.randomUUID().replaceAll("-", "").slice(0, 16);

/** The first avatar every account gets: a random seed, a random style and background. */
export function randomAvatar(): AvatarSpec {
  const pick = <T,>(xs: readonly T[], fallback: T): T => xs[Math.floor(Math.random() * xs.length)] ?? fallback;
  return {
    style: pick(AVATAR_STYLES, AVATAR_STYLES[0]).id,
    seed: newSeed(),
    options: { backgroundColor: pick(AVATAR_BACKGROUNDS, AVATAR_BACKGROUNDS[0]).hex },
  };
}

const UNREACHABLE = "We can't reach your profile right now.";

async function call(init?: RequestInit): Promise<Result<Me>> {
  let res: Response;
  try {
    res = await fetch("/api/me", { ...init, headers: { "content-type": "application/json", ...init?.headers } });
  } catch {
    return err(UNREACHABLE);
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) return err(isObj(body) && typeof body.error === "string" ? body.error : UNREACHABLE);
  const me = parseMe(body);
  return me ? ok(me) : err("Your profile came back in a shape we couldn't read.");
}

export const meApi = {
  read: () => call(),
  save: (patch: { avatar?: AvatarSpec; name?: string }) => call({ method: "PATCH", body: JSON.stringify(patch) }),
};

// One copy of the profile per tab, shared by the header menu, the account page
// and Your decks, so the first-sign-in avatar is made once, not per component.
let current: Me | null = null;
let pending: Promise<Result<Me>> | null = null;
const subscribers = new Set<() => void>();

export const meStore = {
  get: (): Me | null => current,
  subscribe(fn: () => void): () => void {
    subscribers.add(fn);
    return () => subscribers.delete(fn);
  },
  set(me: Me | null): void {
    current = me;
    for (const fn of subscribers) fn();
  },
  /** Loads the profile once; an account with no avatar yet gets a random one, saved. */
  load(): Promise<Result<Me>> {
    pending ??= (async () => {
      const read = await meApi.read();
      if (!read.ok) {
        pending = null;
        return read;
      }
      let me = read.value;
      if (!me.avatar) {
        const saved = await meApi.save({ avatar: randomAvatar() });
        if (saved.ok) me = saved.value;
      }
      meStore.set(me);
      return ok(me);
    })();
    return pending;
  },
  /** On sign-out: the next user in this tab starts clean. */
  clear(): void {
    pending = null;
    meStore.set(null);
  },
};
