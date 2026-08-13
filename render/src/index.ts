/**
 * render — the single-file exporter (v1).
 *
 * Bundles web/src (the pure renderer + design tokens) via esbuild and produces
 * the one self-contained .html deck: fonts and images embedded as data URIs,
 * motion inlined, connect-src 'none'. The exporter itself lands in phase 05;
 * this entry exists so the package typechecks from day one.
 */
export {};
