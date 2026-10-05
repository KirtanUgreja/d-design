// E5 on real pixels (docs/v4/design-engine.md -> QA metrics): the slide is
// screenshotted with its field text hidden, and each field's text colour is
// measured against the worst 10% of the background pixels behind it. This sees
// what the computed-colour check cannot: text over a texture, a numeral or a
// field edge. arg: {png: base64, boxes: [{field, l, t, r, b, color: [r,g,b]}]}
async (arg) => {
  const img = new Image();
  img.src = "data:image/png;base64," + arg.png;
  await img.decode();
  const c = document.createElement("canvas");
  c.width = img.width; c.height = img.height;
  const g = c.getContext("2d", { willReadFrequently: true });
  g.drawImage(img, 0, 0);
  const k = img.width / 1920;
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const lum = (r, gg, b) => 0.2126 * lin(r) + 0.7152 * lin(gg) + 0.0722 * lin(b);
  // APCA-W3 0.1.9, as engine/design/color.py
  const ay = (r, gg, b) => { const y = 0.2126729 * (r / 255) ** 2.4 + 0.7151522 * (gg / 255) ** 2.4 + 0.072175 * (b / 255) ** 2.4; return y > 0.022 ? y : y + (0.022 - y) ** 1.414; };
  const apca = (t, bg) => {
    if (Math.abs(bg - t) < 0.0005) return 0;
    if (bg > t) { const s = (bg ** 0.56 - t ** 0.57) * 1.14; return s < 0.1 ? 0 : (s - 0.027) * 100; }
    const s = (bg ** 0.65 - t ** 0.62) * 1.14; return s > -0.1 ? 0 : (s + 0.027) * 100;
  };
  const out = [];
  for (const b of arg.boxes) {
    const x = Math.max(0, Math.floor(b.l * k)), y = Math.max(0, Math.floor(b.t * k));
    const w = Math.min(c.width - x, Math.ceil((b.r - b.l) * k)), h = Math.min(c.height - y, Math.ceil((b.b - b.t) * k));
    if (w < 1 || h < 1) continue;
    const d = g.getImageData(x, y, w, h).data;
    const [tr, tg, tb] = b.color, tl = lum(tr, tg, tb), ta = ay(tr, tg, tb);
    const ratios = [], lcs = [];
    const stride = Math.max(1, Math.floor(Math.sqrt((w * h) / 4000))); // about 4,000 samples
    for (let yy = 0; yy < h; yy += stride) for (let xx = 0; xx < w; xx += stride) {
      const i = (yy * w + xx) * 4, bl = lum(d[i], d[i + 1], d[i + 2]);
      ratios.push((Math.max(tl, bl) + 0.05) / (Math.min(tl, bl) + 0.05));
      lcs.push(Math.abs(apca(ta, ay(d[i], d[i + 1], d[i + 2]))));
    }
    ratios.sort((p, q) => p - q); lcs.sort((p, q) => p - q);
    const at = (a) => a[Math.floor(a.length * 0.1)];
    out.push({ field: b.field, wcag: at(ratios), apca: at(lcs) });
  }
  return out;
}
