// Runs in Chromium against the QA document. Measures every slide and returns
// defects as data. It judges nothing: thresholds are numbers, and a slide it
// cannot measure is reported as unmeasured, never as clean.
// docs/v4/design-engine.md -> "QA metrics". arg: {slides:{id:{name:text}}, theme:{colors,families,sizes}}
(arg) => {
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const rgb = (c) => { const m = c.match(/[\d.]+/g); return m ? m.map(Number) : [0, 0, 0, 0]; };
  const lum = ([r, g, b]) => {
    const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const opaque = (c) => { const v = rgb(c); return v.length < 4 || v[3] > 0; };
  const SMALL = /^(kicker|source|stat-label|label|caption|folio)/;
  const out = {};

  for (const host of document.querySelectorAll(".dd-slide")) {
    const id = host.dataset.slide, root = host.shadowRoot, errors = [], warnings = [];
    const add = (code, field, measured, threshold) => errors.push({ code, field, measured: String(measured), threshold: String(threshold) });
    // Reported and tracked, never repaired: a widow is a blemish, not a break.
    const warn = (code, field, measured, threshold) => warnings.push({ code, field, measured: String(measured), threshold: String(threshold) });
    if (!root || !root.querySelector(".s")) { out[id] = { measured: false, errors: [], fingerprint: "" }; continue; }
    const box = host.getBoundingClientRect();
    const want = arg.slides[id] || {};
    const rel = (r) => ({ l: r.left - box.left, t: r.top - box.top, r: r.right - box.left, b: r.bottom - box.top });

    // background actually behind an element: the nearest opaque ancestor colour.
    const bgOf = (el) => {
      for (let n = el; n; n = n.parentElement || (n.getRootNode().host === host ? null : n.getRootNode().host)) {
        const c = getComputedStyle(n).backgroundColor;
        if (opaque(c)) return rgb(c);
      }
      return rgb(getComputedStyle(host).backgroundColor);
    };

    // E6 completeness: every planned field exactly once, with the same words.
    const fields = [...root.querySelectorAll("[data-field]")];
    for (const name of Object.keys(want)) {
      const found = fields.filter((f) => f.dataset.field === name);
      if (found.length !== 1) add("E6", name, found.length + " nodes", "exactly 1");
      else if (norm(found[0].textContent) !== norm(want[name])) add("E6", name, "text differs: " + norm(found[0].textContent).slice(0, 80), "the planned text, unchanged");
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      if (!norm(n.textContent) || n.parentElement.closest("style")) continue;
      const deco = n.parentElement.closest("[data-deco]");
      if (n.parentElement.closest("[data-field]")) continue;
      if (n.parentElement.closest("dd-chart")) continue; // our component's labels
      if (!deco) add("E6", null, "stray text: " + norm(n.textContent).slice(0, 60), "text only in data-field or data-deco");
      else if (norm(deco.textContent).split(" ").length > 3) add("E6", null, "data-deco over 3 words", "3 words");
    }

    const rects = [], boxes = [];
    for (const el of fields) {
      const name = el.dataset.field, cs = getComputedStyle(el), r = rel(el.getBoundingClientRect());
      const size = parseFloat(cs.fontSize);
      if (r.r - r.l < 1 || r.b - r.t < 1) { add("E1", name, "not visible", "visible"); continue; }
      // The ink box: the union of the words themselves. Tight display leading
      // makes scrollHeight exceed clientHeight without anything being cut off,
      // so the element box is the wrong thing to measure.
      const range = document.createRange(), tops = [];
      const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let words = 0; const ink = { l: 1e9, t: 1e9, r: -1e9, b: -1e9 };
      for (let n = tw.nextNode(); n; n = tw.nextNode()) {
        const re = /\S+/g; let m;
        while ((m = re.exec(n.textContent))) {
          range.setStart(n, m.index); range.setEnd(n, m.index + m[0].length);
          const q = range.getBoundingClientRect(); if (!q.height) continue;
          const k = rel(q); tops.push(Math.round(q.top)); words++;
          ink.l = Math.min(ink.l, k.l); ink.t = Math.min(ink.t, k.t); ink.r = Math.max(ink.r, k.r); ink.b = Math.max(ink.b, k.b);
        }
      }
      if (!words) { add("E1", name, "no visible text", "visible"); continue; }
      // E1 clipped or off the canvas; E2 inside the safe area
      if (ink.l < -1 || ink.t < -1 || ink.r > 1921 || ink.b > 1081) add("E1", name, `text at ${Math.round(ink.l)},${Math.round(ink.t)}–${Math.round(ink.r)},${Math.round(ink.b)}`, "inside 0,0–1920,1080");
      else if (ink.l < 64 || ink.r > 1856 || ink.t < 40 || ink.b > 1040) add("E2", name, `${Math.round(Math.min(ink.l, ink.t, 1920 - ink.r, 1080 - ink.b))}px from the edge`, "64px");
      if (ink.r > r.r + 2) add("E1", name, "text runs past its box on the right", "fits");
      for (let n = el.parentElement; n; n = n.parentElement) {
        if (getComputedStyle(n).overflow === "visible") continue;
        const p = rel(n.getBoundingClientRect());
        if (ink.l < p.l - 1 || ink.r > p.r + 1 || ink.t < p.t - 8 || ink.b > p.b + 8) { add("E1", name, "clipped by an ancestor", "fully visible"); break; }
      }
      // E4 type size
      const min = name === "headline" ? 56 : SMALL.test(name) ? 22 : 32;
      if (size < min) add("E4", name, size + "px", min + "px");
      // E5 contrast against the ground actually behind it
      const c = ratio(rgb(cs.color), bgOf(el)), need = size >= 64 ? 3 : 4.5;
      if (c < need) add("E5", name, c.toFixed(2), need);
      // E7 computed style must be theme values
      const fam = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
      if (!arg.theme.families.includes(fam)) add("E7", name, "font-family " + fam, "a theme font");
      if (!arg.theme.sizes.includes(Math.round(size))) add("E7", name, "font-size " + size + "px", "a var(--t-…) size");
      if (!arg.theme.colors.includes(cs.color)) add("E7", name, "color " + cs.color, "a theme colour");
      // E8 the face really loaded
      if (!document.fonts.check(`${cs.fontWeight} ${size}px "${fam}"`)) add("E8", name, `${fam} ${cs.fontWeight}`, "an embedded weight");
      // E9 wrapping
      const lines = [...new Set(tops)].sort((a, b) => a - b);
      if (name === "headline" && lines.length > 4) add("E9", name, lines.length + " lines", "4 lines");
      if (words >= 3 && lines.length === words) add("E9", name, "one word per line", "wider box");
      // E3 lines of one field set tighter than the display face survives
      if (lines.length >= 2 && fam === arg.theme.display) {
        const lh = parseFloat(cs.lineHeight) / size;
        if (lh < arg.theme.leading - 0.005) add("E3", name, "line-height " + lh.toFixed(2), String(arg.theme.leading));
      }
      if (name === "headline" && lines.length >= 2 && words >= 5 && tops.filter((t) => t === lines[lines.length - 1]).length === 1) warn("W7", name, "single word on the last line", "at least 2 words");
      rects.push({ name, el, r, layer: !!el.closest("[data-layer]") });
      boxes.push({ field: name, l: ink.l, t: ink.t, r: ink.r, b: ink.b, color: rgb(cs.color).slice(0, 3), size, lines: lines.length, chars: norm(el.textContent).length, contrast: c });
    }
    // E3 collisions between fields
    for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
      const a = rects[i], b = rects[j];
      if (a.el.contains(b.el) || b.el.contains(a.el) || a.layer || b.layer) continue;
      const w = Math.min(a.r.r, b.r.r) - Math.max(a.r.l, b.r.l), h = Math.min(a.r.b, b.r.b) - Math.max(a.r.t, b.r.t);
      if (w > 4 && h > 4) add("E3", a.name, `overlaps ${b.name} by ${Math.round(w)}x${Math.round(h)}px`, "no overlap");
    }
    // E7 for everything else: no colour outside the theme
    for (const el of root.querySelectorAll("*")) {
      if (el.tagName === "STYLE") continue;
      const cs = getComputedStyle(el);
      for (const [k, v] of [["background-color", cs.backgroundColor], ["border-color", parseFloat(cs.borderTopWidth) + parseFloat(cs.borderLeftWidth) + parseFloat(cs.borderBottomWidth) + parseFloat(cs.borderRightWidth) > 0 ? cs.borderTopColor : null]]) {
        if (v && opaque(v) && !arg.theme.colors.includes(v)) { add("E7", el.dataset.field || null, k + " " + v, "a theme colour"); break; }
      }
    }
    // E11 an empty block: a solid field with nothing on it. Rules, bars and
    // patterns pass; so does a field that text sits on or over.
    const s = root.querySelector(".s"), scs = getComputedStyle(s);
    const groundOf = (el) => (el.parentElement ? bgOf(el.parentElement).join() : "");
    for (const el of root.querySelectorAll("*")) {
      if (el === s || el.tagName === "STYLE" || el.querySelector("[data-field]") || el.closest("[data-field]")) continue;
      const texture = el.tagName === "DD-TEXTURE";
      if (texture && el.getAttribute("kind") !== "solid") continue;
      const bg = getComputedStyle(el).backgroundColor;
      if (!texture && (!opaque(bg) || rgb(bg).join() === groundOf(el))) continue;
      const r = rel(el.getBoundingClientRect()), w = r.r - r.l, h = r.b - r.t;
      if (Math.min(w, h) < 48 || w * h < 0.03 * 1920 * 1080) continue;
      const under = rects.some((f) => Math.min(f.r.r, r.r) - Math.max(f.r.l, r.l) > 4 && Math.min(f.r.b, r.b) - Math.max(f.r.t, r.t) > 4);
      if (!under) add("E11", null, `empty block ${Math.round(w)}x${Math.round(h)}px`, "a solid field carries text, or is under 48px thick");
    }
    const centred = rects.length && rects.filter((x) => getComputedStyle(x.el).textAlign === "center").length > rects.length / 2;
    const fingerprint = [scs.display, scs.gridTemplateColumns.split(" ").length, scs.gridTemplateRows.split(" ").length, centred ? "c" : "l", fields.map((f) => f.dataset.field.replace(/-\d+$/, "")).join(">"), root.querySelectorAll("dd-texture").length].join("|");
    out[id] = { measured: true, errors, warnings, fingerprint, centred, boxes };
  }
  return out;
}
