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

Abstract 3D is the one that will carry actual usage. Most users have no model of anything, and a scroll-driven abstract form under `cinematic-dark`'s dramatic lighting is beautiful without claiming to be a product.

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

**Failure:** no WebGL, GPU blocklist, context lost, or budget exceeded → static render, no error, no empty frame. Every 3D scene needs a poster image, generated server-side at publish. Not a fallback — a requirement.

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

## Honest assessment

3D is a specialty, not a feature. Asset pipelines, draw-call budgets, mobile GPUs, memory ceilings, format conversion, and a graceful fallback for every failure — each is a project.

It is last in the build order for that reason, and the build order is designed so stopping before it still leaves v3 coherent: derived art directions, twelve languages, personalized links, analytics, and live data is a complete release.

Ship 3D when it is genuinely good. A broken 3D scene on a launch page is worse than no 3D scene.
