import { describe, expect, it } from 'vitest';

import { assertNoCredentials, describeFailure } from './server';
import { renderDocument } from './render-scene';

// The control that justifies running a browser in this service at all
// (docs/techstack/backend.md — the trust split). Asserted in code as well as in
// the compose file, because a control that lives only in configuration is one
// nobody notices the loss of: a `render` that acquired a DATABASE_URL works
// perfectly and has quietly collapsed the reason it was safe.
describe('render holds no credential', () => {
  it('accepts an environment with none of them', () => {
    expect(() => assertNoCredentials({ PORT: '3200' })).not.toThrow();
  });

  it.each([
    'DATABASE_URL',
    'MIGRATION_DATABASE_URL',
    'S3_ACCESS_KEY',
    'S3_SECRET_KEY',
    'OPENROUTER_API_KEY',
  ])('refuses to start when %s is present', (name) => {
    expect(() => assertNoCredentials({ [name]: 'anything' })).toThrow(/no credential/);
  });

  it('treats an empty value as absent, so a compose file may blank one out', () => {
    expect(() => assertNoCredentials({ DATABASE_URL: '' })).not.toThrow();
  });
});

describe('the document it renders', () => {
  const scene = {
    id: 'one',
    intent: 'hook' as const,
    layout: 'centered' as const,
    blocks: [{ id: 'h', props: { type: 'headline' as const, text: 'Hello' } }],
  };

  it('is the renderer web ships, not a copy', () => {
    const html = renderDocument([scene], 'cinematic-dark', true);
    // The scene anchor and the fit shell are the renderer's own output; if this
    // file ever grew its own markup, these would be the first things to drift.
    expect(html).toContain('id="scene-one"');
    expect(html).toContain('Hello');
  });

  it('inlines the real typefaces rather than falling back', () => {
    // The first working screenshot came back set in Times. A fallback face
    // looks plausible and measures differently, which makes phase 09 a vision
    // model reviewing the wrong image and phase 13's overflow arithmetic wrong.
    const html = renderDocument([scene], 'cinematic-dark', true);
    expect(html).toContain("font-family:'Fraunces'");
    expect(html).toContain('data:font/woff2;base64,');
  });

  it('carries the art direction as custom properties, from the one emitter', () => {
    const dark = renderDocument([scene], 'cinematic-dark', true);
    const light = renderDocument([scene], 'editorial-light', true);
    expect(dark).toContain('--bg:');
    // Two art directions, one code path — the same claim the browser path makes.
    expect(dark).not.toBe(light);
  });

  it('emits no gradient, in the service as in the browser', () => {
    expect(renderDocument([scene], 'cinematic-dark', true)).not.toMatch(/gradient\(/);
  });
});

// A scene tree is a customer's unreleased launch copy, so a validation failure
// reports *shape*, never content. The first version of the handler returned
// `error.message`, which for a Zod error is the whole issue list — values
// included.
describe('a failure says what was wrong, not what was in it', () => {
  it('reports paths and codes from a Zod error', () => {
    const zodLike = {
      issues: [{ code: 'invalid_type', path: ['blocks', 0, 'props', 'text'] }],
    };
    const message = describeFailure(zodLike);
    expect(message).toContain('invalid_type');
    expect(message).toContain('blocks.0.props.text');
  });

  it('never carries the offending value', () => {
    const secret = 'Project Halcyon ships in March';
    const zodLike = {
      issues: [{ code: 'too_big', path: ['blocks', 0], input: secret }],
      message: `Too big: received "${secret}"`,
    };
    expect(describeFailure(zodLike)).not.toContain(secret);
  });
});
