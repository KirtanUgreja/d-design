// Shared across all three comps. Not part of the product — the renderer in
// phase 04 will use Motion (motion/react) and a real toggle component; this
// is the minimum vanilla JS that lets the comps be judged honestly:
//   1. the reveal/emphasize/parallax timing actually running, at the real
//      durations and easing, not described in prose
//   2. the in-page reduced-motion toggle art-direction.md requires alongside
//      the OS-level media query
//   3. the RTL mirror, which is the cheapest possible proof the
//      logical-properties discipline held

(function () {
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');

  function motionOff() {
    return document.documentElement.hasAttribute('data-motion-off') || media.matches;
  }

  // Fires once, at 25% visible — --trigger in tokens.css.
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        entry.target.classList.add('is-revealed');
        observer.unobserve(entry.target);
      }
    },
    { threshold: 0.25 },
  );

  document.querySelectorAll('[data-motion]').forEach((el) => {
    if (el.dataset.motion === 'none' || motionOff()) {
      el.classList.add('is-revealed');
      return;
    }
    observer.observe(el);
  });

  // Parallax: 0.15x scroll delta, clamped to +/-80px. translateY is one of
  // the two axes that does NOT invert under RTL (art-direction.md's motion
  // table) — unlike translateX, which would need a manual flip.
  const parallaxEls = motionOff() ? [] : [...document.querySelectorAll('[data-motion="parallax"]')];
  if (parallaxEls.length) {
    let ticking = false;
    const apply = () => {
      const mid = window.scrollY + window.innerHeight / 2;
      for (const el of parallaxEls) {
        const rect = el.getBoundingClientRect();
        const elMid = rect.top + window.scrollY + rect.height / 2;
        const delta = Math.max(-80, Math.min(80, (mid - elMid) * 0.15));
        el.style.transform = `translateY(${delta}px)`;
      }
      ticking = false;
    };
    window.addEventListener(
      'scroll',
      () => {
        if (!ticking) {
          requestAnimationFrame(apply);
          ticking = true;
        }
      },
      { passive: true },
    );
    apply();
  }

  // The in-page motion toggle art-direction.md requires alongside the OS
  // setting: "most people don't know it exists." A page-level control
  // belongs in the runtime so every published experience gets it for free —
  // this button is the phase-02 stand-in for that runtime control.
  const toggle = document.querySelector('[data-motion-toggle]');
  if (toggle) {
    toggle.addEventListener('click', () => {
      const html = document.documentElement;
      const next = !html.hasAttribute('data-motion-off');
      html.toggleAttribute('data-motion-off', next);
      toggle.setAttribute('aria-pressed', String(next));
      toggle.textContent = next ? 'Motion: off' : 'Motion: on';
    });
  }

  // RTL mirror check — "dir=rtl on the root mirrors correctly with no CSS
  // change" is a checklist item this phase requires be verifiable, not
  // assumed. Toggling here is the cheapest possible proof.
  const rtl = document.querySelector('[data-rtl-toggle]');
  if (rtl) {
    rtl.addEventListener('click', () => {
      const html = document.documentElement;
      const next = html.dir === 'rtl' ? 'ltr' : 'rtl';
      html.dir = next;
      rtl.setAttribute('aria-pressed', String(next === 'rtl'));
      rtl.textContent = next === 'rtl' ? 'Direction: RTL' : 'Direction: LTR';
    });
  }
})();
