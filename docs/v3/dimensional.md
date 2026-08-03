# 3D Scenes

Scroll-driven WebGL, styled by the art direction like everything else.

Spectacular for product launches, and the feature most likely to be half-built. **It is last in the build order, and v3 should ship without it rather than with it broken.**

## One new primitive

```ts
Model3D {
  assetId: string;
  source: 'upload' | 'stock' | 'abstract';
  camera: 'orbit' | 'scroll-rotate' | 'scroll-dolly' | 'static';
  label?: string;
}
```

No lighting props. No material props. No colors, no intensities, no camera angles in degrees.

The v1 invariant holds without exception here: **the art direction styles the 3D scene.** A `Model3D` block says *what* and *how it moves with scroll*. Everything about how it looks comes from tokens.

19 primitives total. Live data and personalization added zero.

## The `environment` token group

The fifth group, added to every art direction.

```ts
EnvironmentTokens {
  lighting:   'studio' | 'dramatic' | 'soft' | 'rim';
  background: 'void' | 'gradient' | 'environment-map';
  material:   'matte' | 'satin' | 'glossy' | 'metallic';
  exposure:   number;
  shadow:     'none' | 'contact' | 'soft' | 'hard';
  cameraEase: MotionVocabularyRef;
}
```

Enums, not raw values — the same discipline as everywhere else. An AD picks `dramatic` lighting; the renderer decides what that means.

Concretely: `cinematic-dark` lights a product with `dramatic` + `rim` against a `void` background, glossy, hard shadows. `editorial-light` uses `soft` lighting on a `gradient`, matte, contact shadow. Same model, same block, unrecognizably different scene.

**This is what keeps the reskin guarantee alive.** Without an `environment` group, a 3D scene would render identically under every art direction and look pasted in from another product — and reskin would stop being true of the whole page.

`cameraEase` references a motion vocabulary, so camera movement inherits the experience's motion character. `mechanical-snap` rotates a product very differently than `cinematic-slow`.

## Assets — never generate the product

Three sources. AI image-to-3D is deliberately absent.

| Source | What |
|---|---|
| **Stock primitives** | Devices, packaging, generic forms. Composable, cheap, and it will look generic if leaned on |
| **Abstract 3D** | Shapes, materials, environments — generated as geometry, not photographed. Always on-brand, no accuracy risk. The 3D sibling of `AbstractVisual` |
| **Upload** | GLB/USDZ from the customer's design team. Hardware companies have these; nobody else does |

The refusal is the same principle as v1's ban on AI-generated product imagery: **a plausible-but-wrong render of the thing being sold is a credibility problem no quality bar fixes.** Image-to-3D on real products produces exactly that — a mesh that is 90% right, which is worse than no mesh.

### An uploaded model is hostile bytes

The upload row adds GLB, Draco, and meshopt decoders to the project. These are compression codecs parsing attacker-supplyable binary, and they sit in the same class as PDF and image decoders in [../security/platform-and-packages.md](../security/platform-and-packages.md) — historically a source of memory-corruption bugs, with decompression bombs as the obvious shape.

So they run where every other hostile parser runs: **the fetch worker**, with no database, no VPC route, and nothing worth stealing ([../techstack/backend.md](../techstack/backend.md)). The performance budgets below double as security caps, and **they are enforced before the decode, not after** — a file claiming 150k triangles must be rejected on its declared and actual size before a decoder allocates against it. A budget checked after parsing is a budget that has already run the attacker's input.

Abstract 3D is the one that will carry actual usage. Most users have no model of anything, and a scroll-driven abstract form under `cinematic-dark`'s dramatic lighting is beautiful without claiming to be a product.

## The stack — and why this got easier

**Three.js + React Three Fiber**, with **WebGPU as the primary renderer and WebGL2 as the fallback.**

That recommendation would have been premature a year earlier. Three things changed:

| | Status |
|---|---|
| **WebGPU** | Reached **Baseline in January 2026**, ~82% global support. Chrome 113+, Edge 113+, Safari 26+. Firefox is the notable holdout — still not on by default as of mid-2026 |
| **Three.js `WebGPURenderer`** | Production-ready with **zero configuration since r171** (September 2025). Migration from `WebGLRenderer` is often a one-line swap |
| **React Three Fiber** | Renderer is overridable via the `Canvas` `gl` prop, so the switch is a prop — and R3F is the natural fit for a React renderer that already composes scenes from a typed tree |

Figma began its production WebGPU rollout in September 2025, ramping by GPU type, OS, and browser. For a B2B and prosumer audience in 2026, **WebGPU primary with a WebGL2 fallback for the ~5–10% tail** is the shipping consensus, and Three.js handles the fallback rather than you.

This does not make 3D cheap — see the honest assessment at the end of this document. It makes the *renderer* choice a non-decision, which was never the hard part.

## Performance

This is where the feature lives or dies. Every item is a requirement, not an optimization.

| | Budget |
|---|---|
| Model file | ≤ 5MB compressed, Draco/meshopt |
| Triangles | ≤ 150k |
| Textures | ≤ 2048², KTX2 |
| Draw calls | ≤ 50 per scene |
| Instances | One `Model3D` per scene, maximum |

**Loading:** never block the page. The scene renders its poster frame; 3D swaps in when ready. A visitor on a slow connection sees a complete, beautiful page that simply never becomes interactive.

**Mobile:** reduced texture resolution, capped device pixel ratio, shadows off. Test on a mid-range Android, not on a recent iPhone.

**Failure — three tiers, in order:** WebGPU unavailable → WebGL2 (Three.js handles this). WebGL2 unavailable, GPU blocklisted, context lost, or budget exceeded → **static poster render, no error, no empty frame.** Every 3D scene needs a poster image generated at publish. Not a fallback — a requirement, and the same asset the slides-mode degradation uses.

**Posters are generated in the job worker** ([../techstack/backend.md](../techstack/backend.md)): rendering a scene to an image needs the renderer and a browser together, it is slow enough to sit past a function timeout, and its input is a validated scene tree from your own database rather than hostile bytes. It enqueues in the same transaction as the publish, so a rolled-back publish leaves no orphaned poster job. Note the split from the paragraph above — the fetch worker *parses* an uploaded model, the job worker *renders* an approved scene, and they are different containers for exactly that reason.

**Reduced motion:** static frame, no auto-rotation, no scroll-driven camera.

## Interaction with everything else

| | Behavior |
|---|---|
| **Slides mode** | Scroll-driven cameras have no scroll. `orbit` and `static` work; `scroll-rotate`/`scroll-dolly` fall back to `static`. Editor warns on mode switch |
| **Reskin** | Environment tokens swap; the model does not move. Cheapest possible reskin |
| **Localization** | `label` transcreates. The scene does not mirror in RTL |
| **Export / embed** | Embedded 3D honors the same budgets. An iframe on someone else's page is not licence to ship 5MB more |

## Verification

- Mid-range Android: interactive, within budget, no jank on scroll
- WebGL disabled → poster renders, no error, no gap
- Context loss mid-scroll → falls back to poster cleanly
- Same model under 3 ADs → visibly, deliberately different lighting and material
- Slides mode → scroll cameras degrade to static, warning shown
- Reduced motion → static frame, no camera movement
- Every published 3D scene has a generated poster
- A model declaring modest geometry and decompressing to gigabytes is rejected **before** the decoder allocates
- A malformed GLB fails inside the fetch worker and reaches no database

## Honest assessment

3D is a specialty, not a feature. Asset pipelines, draw-call budgets, mobile GPUs, memory ceilings, format conversion, and a graceful fallback for every failure — each is a project.

It is last in the build order for that reason, and the build order is designed so stopping before it still leaves v3 coherent: derived art directions, twelve languages, personalized links, analytics, and live data is a complete release.

Ship 3D when it is genuinely good. A broken 3D scene on a launch page is worse than no 3D scene.
