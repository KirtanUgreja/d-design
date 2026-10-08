"use client";
// A profile avatar, drawn here in the browser by the DiceBear library from
// {style, seed, options} (master plan A6). Never fetched from api.dicebear.com:
// the style definitions ship with the app and load on demand, one per style.
import { Avatar as DiceAvatar, Style } from "@dicebear/core";
import { useEffect, useState, useSyncExternalStore } from "react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { meStore, type AvatarSpec, type AvatarStyle, type Me } from "@/lib/auth-me";

const LOADERS: Record<AvatarStyle, () => Promise<unknown>> = {
  notionists: () => import("@dicebear/styles/notionists.json").then((m) => m.default),
  lorelei: () => import("@dicebear/styles/lorelei.json").then((m) => m.default),
  "open-peeps": () => import("@dicebear/styles/open-peeps.json").then((m) => m.default),
  thumbs: () => import("@dicebear/styles/thumbs.json").then((m) => m.default),
  shapes: () => import("@dicebear/styles/shapes.json").then((m) => m.default),
  "pixel-art": () => import("@dicebear/styles/pixel-art.json").then((m) => m.default),
};

const styles = new Map<AvatarStyle, Promise<Style>>();

function loadStyle(id: AvatarStyle): Promise<Style> {
  let s = styles.get(id);
  if (!s) {
    s = LOADERS[id]().then((def) => new Style(def));
    styles.set(id, s);
  }
  return s;
}

/** The SVG as a data URI, or null until the style has loaded. */
export function useAvatarUri(spec: AvatarSpec | null): string | null {
  const [drawn, setDrawn] = useState<{ key: string; uri: string } | null>(null);
  const key = spec ? `${spec.style}:${spec.seed}:${spec.options.backgroundColor}` : "";
  useEffect(() => {
    if (!spec) return;
    let live = true;
    loadStyle(spec.style)
      .then((style) => {
        const uri = new DiceAvatar(style, {
          seed: spec.seed,
          backgroundColor: [spec.options.backgroundColor],
          backgroundColorFill: "solid", // the chrome has no gradients (docs/design/brand.md)
        }).toDataUri();
        if (live) setDrawn({ key, uri });
      })
      .catch(() => {
        if (live) setDrawn(null);
      });
    return () => {
      live = false;
    };
    // `key` captures every field of spec that changes the drawing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return drawn && drawn.key === key ? drawn.uri : null;
}

const initials = (name: string, email: string): string =>
  (name.trim() || email)
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");

export function ProfileAvatar({
  spec,
  name,
  email,
  size = "default",
  className,
}: {
  spec: AvatarSpec | null;
  name: string;
  email: string;
  size?: "default" | "sm" | "lg";
  className?: string;
}) {
  const uri = useAvatarUri(spec);
  return (
    <Avatar size={size} className={className} data-avatar-seed={spec?.seed ?? ""} data-avatar-style={spec?.style ?? ""}>
      {uri && <AvatarImage src={uri} alt="" />}
      <AvatarFallback>{initials(name, email)}</AvatarFallback>
    </Avatar>
  );
}

/** The signed-in user's profile, loaded once per tab (and their first avatar made). */
export function useMe(): Me | null {
  const me = useSyncExternalStore(meStore.subscribe, meStore.get, () => null);
  useEffect(() => {
    void meStore.load();
  }, []);
  return me;
}
