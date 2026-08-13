/**
 * The design-family token registry — the renderer's half of the design space.
 *
 * The family *identities* live in api/schema/design_families.py (the Pydantic
 * source of truth). This module maps the same family ids to concrete CSS
 * custom-property values. The two registries are keyed by id; a family id in
 * one but not the other is a bug the acceptance run's fingerprint check
 * surfaces as a mismatch.
 *
 * The model never emits a presentational value (no hex, no px, no font, no
 * duration). The renderer applies these tokens, and only these tokens. This is
 * what keeps a deck cohesive — constant design system — while each slide is
 * individually generated.
 */

/** A complete set of design tokens for one family, as CSS custom properties. */
export type DesignTokens = {
  id: string;
  css: Record<string, string>;
};

/** The motion vocabulary: how the family reveals, and the pacing. */
export type MotionVocabulary = {
  reveal: 'fade' | 'rise' | 'slide' | 'mask' | 'none';
  pacing: 'calm' | 'steady' | 'quick';
};

export type DesignFamilySpec = {
  id: string;
  tokens: DesignTokens;
  motion: MotionVocabulary;
};

const base = {
  '--dds-font-display': "'Inter', system-ui, sans-serif",
  '--dds-font-body': "'Inter', system-ui, sans-serif",
  '--dds-radius': '0px',
  '--dds-space': '8px',
  '--dds-ink': '#111111',
  '--dds-paper': '#ffffff',
  '--dds-accent': '#111111',
  '--dds-texture': 'none',
};

/** Keyed by the same family ids as api/schema/design_families.py. */
export const DESIGN_FAMILY_TOKENS: Record<string, DesignFamilySpec> = {
  'editorial-serif': {
    id: 'editorial-serif',
    tokens: {
      id: 'editorial-serif',
      css: {
        ...base,
        '--dds-font-display': "'Source Serif 4', Georgia, serif",
        '--dds-font-body': "'Source Serif 4', Georgia, serif",
        '--dds-ink': '#1a1a18',
        '--dds-paper': '#faf7f2',
        '--dds-accent': '#8a2b16',
        '--dds-texture': 'paper',
      },
    },
    motion: { reveal: 'rise', pacing: 'calm' },
  },
  'brutalist-stencil': {
    id: 'brutalist-stencil',
    tokens: {
      id: 'brutalist-stencil',
      css: {
        ...base,
        '--dds-font-display': "'Archivo Black', 'Inter', sans-serif",
        '--dds-font-body': "'Space Mono', monospace",
        '--dds-ink': '#111111',
        '--dds-paper': '#f4f1ea',
        '--dds-accent': '#d62828',
        '--dds-texture': 'stencil',
      },
    },
    motion: { reveal: 'mask', pacing: 'quick' },
  },
  'swiss-grid': {
    id: 'swiss-grid',
    tokens: {
      id: 'swiss-grid',
      css: {
        ...base,
        '--dds-font-display': "'Inter', system-ui, sans-serif",
        '--dds-font-body': "'Inter', system-ui, sans-serif",
        '--dds-ink': '#101418',
        '--dds-paper': '#f7f8fa',
        '--dds-accent': '#d62828',
        '--dds-texture': 'hairline',
      },
    },
    motion: { reveal: 'slide', pacing: 'steady' },
  },
  'neo-noir': {
    id: 'neo-noir',
    tokens: {
      id: 'neo-noir',
      css: {
        ...base,
        '--dds-font-display': "'Archivo', system-ui, sans-serif",
        '--dds-font-body': "'Archivo', system-ui, sans-serif",
        '--dds-ink': '#e8e6e3',
        '--dds-paper': '#0d0d0f',
        '--dds-accent': '#c9a227',
        '--dds-texture': 'grain',
      },
    },
    motion: { reveal: 'fade', pacing: 'calm' },
  },
  scientific: {
    id: 'scientific',
    tokens: {
      id: 'scientific',
      css: {
        ...base,
        '--dds-font-display': "'IBM Plex Sans', system-ui, sans-serif",
        '--dds-font-body': "'IBM Plex Mono', monospace",
        '--dds-ink': '#10222b',
        '--dds-paper': '#f4f6f8',
        '--dds-accent': '#0f766e',
        '--dds-texture': 'plot',
      },
    },
    motion: { reveal: 'rise', pacing: 'steady' },
  },
  'editorial-sans': {
    id: 'editorial-sans',
    tokens: {
      id: 'editorial-sans',
      css: {
        ...base,
        '--dds-font-display': "'Inter Tight', system-ui, sans-serif",
        '--dds-font-body': "'Inter', system-ui, sans-serif",
        '--dds-ink': '#1c1a17',
        '--dds-paper': '#fbfaf7',
        '--dds-accent': '#b45309',
        '--dds-texture': 'texture',
      },
    },
    motion: { reveal: 'rise', pacing: 'calm' },
  },
  'brutalist-poster': {
    id: 'brutalist-poster',
    tokens: {
      id: 'brutalist-poster',
      css: {
        ...base,
        '--dds-font-display': "'Archivo Black', 'Inter', sans-serif",
        '--dds-font-body': "'Space Mono', monospace",
        '--dds-ink': '#111111',
        '--dds-paper': '#f4f1ea',
        '--dds-accent': '#f4a300',
        '--dds-texture': 'offset',
      },
    },
    motion: { reveal: 'mask', pacing: 'quick' },
  },
  'tech-minimal': {
    id: 'tech-minimal',
    tokens: {
      id: 'tech-minimal',
      css: {
        ...base,
        '--dds-font-display': "'IBM Plex Mono', monospace",
        '--dds-font-body': "'IBM Plex Sans', system-ui, sans-serif",
        '--dds-ink': '#0d1117',
        '--dds-paper': '#ffffff',
        '--dds-accent': '#0969da',
        '--dds-texture': 'hairline',
      },
    },
    motion: { reveal: 'slide', pacing: 'steady' },
  },
  'dark-editorial': {
    id: 'dark-editorial',
    tokens: {
      id: 'dark-editorial',
      css: {
        ...base,
        '--dds-font-display': "'Source Serif 4', Georgia, serif",
        '--dds-font-body': "'Source Serif 4', Georgia, serif",
        '--dds-ink': '#ece7e1',
        '--dds-paper': '#161412',
        '--dds-accent': '#c9a227',
        '--dds-texture': 'grain',
      },
    },
    motion: { reveal: 'fade', pacing: 'calm' },
  },
  'vivid-flat': {
    id: 'vivid-flat',
    tokens: {
      id: 'vivid-flat',
      css: {
        ...base,
        '--dds-font-display': "'Nunito', system-ui, sans-serif",
        '--dds-font-body': "'Nunito', system-ui, sans-serif",
        '--dds-ink': '#1a1a2e',
        '--dds-paper': '#fdf2e9',
        '--dds-accent': '#e63946',
        '--dds-texture': 'flat',
      },
    },
    motion: { reveal: 'rise', pacing: 'quick' },
  },
  'print-specimen': {
    id: 'print-specimen',
    tokens: {
      id: 'print-specimen',
      css: {
        ...base,
        '--dds-font-display': "'Source Serif 4', Georgia, serif",
        '--dds-font-body': "'Source Serif 4', Georgia, serif",
        '--dds-ink': '#141310',
        '--dds-paper': '#f6f2ea',
        '--dds-accent': '#9a3412',
        '--dds-texture': 'paper',
      },
    },
    motion: { reveal: 'rise', pacing: 'calm' },
  },
  'system-mono': {
    id: 'system-mono',
    tokens: {
      id: 'system-mono',
      css: {
        ...base,
        '--dds-font-display': "'Space Mono', monospace",
        '--dds-font-body': "'Space Mono', monospace",
        '--dds-ink': '#0d1117',
        '--dds-paper': '#f6f8fa',
        '--dds-accent': '#238636',
        '--dds-texture': 'plot',
      },
    },
    motion: { reveal: 'mask', pacing: 'steady' },
  },
};

export function familyTokens(id: string): DesignFamilySpec | undefined {
  return DESIGN_FAMILY_TOKENS[id];
}
