/**
 * editor — the editing surface (phase 12).
 *
 * The feature public API. The editor wraps the pure renderer (patterns.md
 * rule 2): selection, the property panel, and the family switcher overlay the
 * rendered output; the renderer core knows nothing about them.
 */
export { createEditorStore } from './editor.store.js';
export type { EditorState } from './editor.store.js';
export { EditorCanvas } from './editor-canvas.js';
export type { EditorCanvasProps } from './editor-canvas.js';
export { PropertyPanel } from './property-panel.js';
export type { PropertyPanelProps } from './property-panel.js';
export { FamilySwitcher } from './family-switcher.js';
export type { FamilySwitcherProps } from './family-switcher.js';
