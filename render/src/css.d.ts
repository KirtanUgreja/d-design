/**
 * Declaration for CSS text imports (esbuild loader: css -> text). The exporter
 * inlines the renderer stylesheet into the single-file artefact; TypeScript
 * needs to know the module shape.
 */
declare module '*.css' {
  const content: string;
  export default content;
}
