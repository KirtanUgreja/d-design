import js from '@eslint/js';
import next from 'eslint-config-next';
import nextTs from 'eslint-config-next/typescript';
import tseslint from 'typescript-eslint';

// The stock rules are table stakes. The custom ones below are the point: they
// are the project-specific invariants prose cannot enforce, and each maps to a
// decision that quietly unravels the product if it drifts.
// docs/coderules/tooling.md -> "The pre-commit gate"

const RENDERER = ['src/features/renderer/**/*.{ts,tsx}'];

// Rule 6. The renderer core runs in three processes — the browser, the app
// server, and (from v2) the render service — and must behave identically in
// all of them. A renderer that branches on where it is running is a published
// page that differs from the edited one, which is the exact guarantee the rule
// protects. Dormant until phase 04; written now, while it costs nothing.
const rendererPurity = [
  {
    selector:
      "MemberExpression[object.object.name='process'][object.property.name='env']",
    message:
      'renderer/ is pure: no process.env. Environment differences are the wrapper’s problem (patterns.md rule 2).',
  },
  {
    selector: "UnaryExpression[operator='typeof'] > Identifier[name='window']",
    message:
      'renderer/ is pure: no `typeof window`. It must behave identically in all three processes.',
  },
  {
    selector: "JSXAttribute[name.name='mode']",
    message:
      'renderer/ takes no `mode` prop. Modes wrap the core and inject behaviour from outside (patterns.md rule 2).',
  },
  {
    selector: "TSPropertySignature[key.name='mode']",
    message: 'renderer/ takes no `mode` prop, and no `mode` in its prop types either.',
  },
  {
    // The no-styling invariant seen from the app side: Tailwind is app chrome,
    // the art direction is CSS custom properties, and no file imports both.
    selector: "JSXAttribute[name.name='className'] > Literal",
    message:
      'No Tailwind (or any literal class string) under renderer/. Styling comes from the art-direction CSS variables (techstack/frontend.md).',
  },
];

export default tseslint.config(
  { ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'] },

  js.configs.recommended,
  ...next,
  ...nextTs,

  {
    files: ['**/*.{ts,tsx,mjs}'],
    rules: {
      // The two non-negotiables a checker flag cannot express.
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      // A leading underscore is the one way to say "deliberately discarded",
      // which destructuring-to-omit needs and nothing else should use.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { varsIgnorePattern: '^_', argsIgnorePattern: '^_' },
      ],

      // Rule 4. A feature is reachable only through its index.
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              group: ['@/features/*/*', '../features/*/*', './features/*/*'],
              message:
                'Import a feature through its index.ts. The index is the whole contract (structure.md).',
            },
            {
              group: ['@/schema/generated/*', '**/schema/generated/*'],
              message:
                'Import from @/schema, not from the generated files it re-exports.',
            },
          ],
        },
      ],

      // security/content-and-web.md. The Slot path is the one place this is
      // allowed, and it is sandboxed there.
      'no-restricted-syntax': [
        'error',
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message:
            'dangerouslySetInnerHTML lives only in the Slot path, behind the sandbox (security/content-and-web.md).',
        },
      ],
    },
  },

  {
    files: RENDERER,
    rules: {
      'no-restricted-syntax': ['error', ...rendererPurity],
      // next/image is a Next.js server feature (the /_next/image optimizer
      // route) — unavailable in the job worker and the render service that
      // run this same tree from v2 on. A plain <img> is the one that behaves
      // identically in all three processes (patterns.md rule 2).
      '@next/next/no-img-element': 'off',
    },
  },

  // Generated. Linting it would report on the emitter's formatting choices,
  // and the fail-on-diff gate is what actually guards this directory.
  { files: ['src/schema/generated/**'], rules: { 'no-restricted-syntax': 'off' } },
);
