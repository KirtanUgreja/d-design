// The player: ours, static, allowed by its hash in the export's CSP
// (docs/v4/plan/26-player-export.md). Slides are Declarative Shadow DOM roots
// written by the engine; nothing here builds markup from deck content except
// the presenter popup, which mirrors those same sanitized roots.
(() => {
  const d = document;
  const slides = [...d.querySelectorAll(".dd-slide")];
  const n = slides.length;
  if (!n) return;
  const body = d.body;
  const count = d.getElementById("dd-count");
  const notesBlock = d.getElementById("dd-notes");
  const notes = notesBlock ? JSON.parse(notesBlock.textContent || "{}") : {};
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const motion = reduced ? "still" : body.dataset.motion || "subtle";
  const ms = { still: 0, subtle: 260, confident: 420 }[motion] || 0;
  let i = 0, step = 0, typed = "", popup = null, started = 0, timer = 0, idle = 0;

  // --- builds: data-build="1..n" fields reveal in steps ----------------------
  const builds = (s) => (s.shadowRoot ? [...s.shadowRoot.querySelectorAll("[data-build]")] : []);
  const steps = (s) => builds(s).reduce((m, e) => Math.max(m, +e.dataset.build || 0), 0);
  const paint = (s, k) => {
    for (const e of builds(s)) {
      const on = (+e.dataset.build || 0) <= k;
      e.style.transition = ms ? `opacity ${ms}ms ease, transform ${ms}ms ease` : "";
      e.style.opacity = on ? "" : "0";
      e.style.transform = on || motion !== "confident" ? "" : "translateY(24px)";
    }
  };
  const revealAll = () => slides.forEach((s) => paint(s, Infinity));

  // --- the stage ------------------------------------------------------------
  const fit = () => {
    const k = Math.min(innerWidth / 1920, innerHeight / 1080);
    d.documentElement.style.setProperty("--dd-k", String(k));
    if (popup && !popup.closed) sizeMinis();
  };
  const show = (to, at) => {
    i = Math.max(0, Math.min(n - 1, to));
    step = at === undefined ? 0 : at;
    slides.forEach((s, j) => s.classList.toggle("on", j === i));
    paint(slides[i], step);
    if (location.hash !== `#${i + 1}`) history.replaceState(null, "", `#${i + 1}`);
    count.textContent = `${i + 1} / ${n}`;
    sync();
  };
  const next = () => {
    if (step < steps(slides[i])) { step += 1; paint(slides[i], step); sync(); }
    else if (i < n - 1) show(i + 1, 0);
  };
  const prev = () => {
    if (step > 0) { step -= 1; paint(slides[i], step); sync(); }
    else if (i > 0) show(i - 1, steps(slides[i - 1]));
  };
  const fromHash = () => {
    const k = parseInt(location.hash.slice(1), 10);
    if (k >= 1 && k <= n && k - 1 !== i) show(k - 1, 0);
  };
  const overview = (on) => {
    body.classList.toggle("dd-overview", on);
    if (on) slides[i].scrollIntoView({ block: "center" });
  };
  const wake = () => {
    body.classList.add("dd-awake");
    clearTimeout(idle);
    idle = setTimeout(() => body.classList.remove("dd-awake"), 2200);
  };

  // --- keys, from the deck window or the presenter popup -----------------------
  const onKey = (e) => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (/^[0-9]$/.test(k)) { typed += k; return; }
    if (k === "Enter" && typed) {
      show(parseInt(typed, 10) - 1, 0);
      typed = "";
      overview(false);
      e.preventDefault();
      return;
    }
    typed = "";
    if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(k)) next();
    else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(k)) prev();
    else if (k === "Home") show(0, 0);
    else if (k === "End") show(n - 1, steps(slides[n - 1]));
    else if (k === "f" || k === "F") {
      if (d.fullscreenElement) d.exitFullscreen(); else d.documentElement.requestFullscreen();
    } else if (k === "o" || k === "O") overview(!body.classList.contains("dd-overview"));
    else if (k === "b" || k === "B" || k === ".") body.classList.toggle("dd-black");
    else if (k === "p" || k === "P") presenter();
    else if (k === "Escape") { typed = ""; overview(false); body.classList.remove("dd-black"); }
    else return;
    e.preventDefault();
  };

  // --- the presenter popup ----------------------------------------------------
  // A blank popup inherits this file's origin, so the deck writes into it
  // directly; a BroadcastChannel is unreliable between file:// pages.
  const pad = (v) => String(v).padStart(2, "0");
  const mini = (target, s) => {
    target.textContent = "";
    if (!s || !s.shadowRoot) return;
    const host = popup.document.createElement("div");
    host.className = "dd-mini";
    host.attachShadow({ mode: "open" }).innerHTML = s.shadowRoot.innerHTML;
    target.appendChild(host);
  };
  const sizeMinis = () => {
    for (const box of popup.document.querySelectorAll(".p-frame")) {
      const m = box.querySelector(".dd-mini");
      if (m) m.style.transform = `scale(${box.clientWidth / 1920})`;
    }
  };
  const tick = () => {
    if (!popup || popup.closed) { clearInterval(timer); return; }
    const s = Math.floor((Date.now() - started) / 1000);
    const now = new Date();
    popup.document.getElementById("p-timer").textContent = `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
    popup.document.getElementById("p-clock").textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}`;
  };
  function sync() {
    if (!popup || popup.closed) return;
    const pd = popup.document;
    mini(pd.getElementById("p-cur"), slides[i]);
    mini(pd.getElementById("p-next"), slides[i + 1]);
    pd.getElementById("p-notes").textContent = notes[slides[i].dataset.slide] || "";
    pd.getElementById("p-count").textContent = `${i + 1} / ${n}` + (steps(slides[i]) ? ` · step ${step}/${steps(slides[i])}` : "");
    sizeMinis();
  }
  function presenter() {
    if (popup && !popup.closed) { popup.focus(); return; }
    popup = window.open("", "dd-presenter", "width=1280,height=800");
    if (!popup) return;
    const pd = popup.document;
    pd.title = `Presenter · ${d.title}`;
    const style = pd.createElement("style");
    style.textContent = d.getElementById("dd-theme").textContent + d.getElementById("dd-presenter-css").textContent;
    pd.head.appendChild(style);
    for (const id of ["p-cur", "p-next", "p-notes", "p-bar"]) {
      const el = pd.createElement("div");
      el.id = id;
      if (id !== "p-notes" && id !== "p-bar") el.className = "p-frame";
      pd.body.appendChild(el);
    }
    for (const id of ["p-timer", "p-clock", "p-count"]) {
      const el = pd.createElement("span");
      el.id = id;
      pd.getElementById("p-bar").appendChild(el);
    }
    popup.addEventListener("keydown", onKey);
    popup.addEventListener("resize", sizeMinis);
    started = Date.now();
    clearInterval(timer);
    timer = setInterval(tick, 1000);
    tick();
    sync();
  }

  // --- wiring -----------------------------------------------------------------
  addEventListener("keydown", onKey);
  addEventListener("resize", fit);
  addEventListener("hashchange", fromHash);
  addEventListener("mousemove", wake);
  addEventListener("beforeprint", revealAll);
  addEventListener("afterprint", () => show(i, step));
  d.getElementById("dd-stage").addEventListener("click", (e) => {
    const host = e.target.closest ? e.target.closest(".dd-slide") : null;
    if (body.classList.contains("dd-overview")) {
      if (host) { show(slides.indexOf(host), 0); overview(false); }
      return;
    }
    if (e.clientX < innerWidth / 3) prev(); else next();
  });
  let x0 = null;
  addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0;
    x0 = null;
    if (Math.abs(dx) > 50) { if (dx < 0) next(); else prev(); }
  });
  window.ddPlayer = { revealAll };
  fit();
  show((parseInt(location.hash.slice(1), 10) || 1) - 1, 0);
})();
