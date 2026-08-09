// SceneRenderer, and nothing else worth exporting (docs/v1/plan/04-renderer.md).

export { SceneRenderer } from './scene-renderer';
export type { SceneRendererProps } from './scene-renderer';

// One leaf, exported deliberately rather than reached for.
//
// `AbstractVisualBlock` is a pure `(props, artDirection)` function with no
// state and no knowledge of a scene, and `/dev/visuals` needs it to put the
// five generators side by side over a real photograph — the review that
// docs/v1/plan/11-visuals-and-slot.md calls "the check most likely to be
// skipped", and the only one that catches a generator fighting an image.
//
// This is not the door rule 2 closes. That rule is about the *editor* reaching
// into `renderer/blocks/` to attach selection behaviour, which would put
// interaction inside the core; the lint rule that forbids the deep import is
// still on, and this is the index granting one named export rather than
// someone bypassing it. If a second leaf ever wants out, that is a signal to
// look again rather than to add a line.
export { AbstractVisualBlock } from './blocks/abstract-visual';
