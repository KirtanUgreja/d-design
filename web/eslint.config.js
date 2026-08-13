import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import boundaries from 'eslint-plugin-boundaries';
import globals from 'globals';

export default tseslint.config(
  { ignores: ['node_modules/', 'src/schema/generated/', 'out/'] },
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
);
