import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import boundaries from 'eslint-plugin-boundaries';
import globals from 'globals';

export default tseslint.config(
  { ignores: ['node_modules/', 'src/schema/generated/', 'out/', '.next/'] },
  {
    files: ['**/*.mjs'],
    languageOptions: { globals: globals.node },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { boundaries },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      'no-restricted-syntax': [
        'error',
        {
          selector: 'TSEnumDeclaration',
          message: 'Use const objects + union types, not TS enum (erasableSyntaxOnly).',
        },
      ],
      'boundaries/element-types': 'error',
    },
    settings: {
      'boundaries/elements': [
        { type: 'feature', pattern: 'src/features/*' },
        { type: 'shared', pattern: 'src/lib', capture: ['lib'] },
      ],
      'boundaries/ignore': ['src/schema/generated/**', '**/*.test.ts', '**/*.test.tsx'],
    },
  },
  {
    // Renderer core purity (patterns.md rule 2, tooling.md lint table):
    // no mode prop, no process.env, no typeof window, no Tailwind classes
    // inside the renderer — the design family's tokens are the only styling.
    files: ['src/features/renderer/**/*.ts', 'src/features/renderer/**/*.tsx'],
    rules: {
      'no-restricted-properties': [
        'error',
        {
          object: 'process',
          property: 'env',
          message: 'The renderer core is pure — no process.env (patterns.md rule 2).',
        },
        {
          property: 'mode',
          message:
            'The renderer core has no mode prop — behavior is injected (patterns.md rule 2).',
        },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "BinaryExpression[operator='typeof'][right.type='Identifier'][right.name='window']",
          message: 'The renderer core is pure — no typeof window (patterns.md rule 2).',
        },
      ],
    },
  },
);
