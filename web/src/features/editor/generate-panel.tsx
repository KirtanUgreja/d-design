/**
 * The generate panel — the pipeline, driven from the editor (v3).
 *
 * The human gate is the point of this component, not decoration: the outline is
 * shown with each claim's provenance before anything is mapped or built, so an
 * invented claim is visible while it is still cheap to reject (v1 spec, the
 * trust device). Approving is what spends the build.
 *
 * Three requests, matching the three stages: interview, then mapping and build
 * on approval. The outline lives in this component's state between them, which
 * is why neither server keeps a draft.
 */
'use client';

import { useState } from 'react';

import type { Built, Outline } from '../generation/index.js';

export type GeneratePanelProps = {
  onGenerated: (built: Built) => void;
};

type Phase = 'idle' | 'outline' | 'building';

export function GeneratePanel({ onGenerated }: GeneratePanelProps) {
  const [topic, setTopic] = useState('');
  const [slideCount, setSlideCount] = useState(6);
  const [audience, setAudience] = useState('');
  const [goal, setGoal] = useState('');

  const [outline, setOutline] = useState<Outline | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);

  async function post(stage: string, body: unknown): Promise<unknown> {
    const res = await fetch(`/api/generate/${stage}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = (await res.json()) as unknown;
    if (!res.ok) {
      const message = (data as { error?: string }).error ?? `generation failed (${res.status})`;
      throw new Error(message);
    }
    return data;
  }

  async function handleInterview() {
    setError(null);
    setPhase('idle');
    try {
      const data = await post('interview', {
        topic,
        slide_count: slideCount,
        audience,
        goal,
      });
      setOutline(data as Outline);
      setPhase('outline');
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleApprove() {
    if (!outline) return;
    setError(null);
    setPhase('building');
    try {
      // Mapping picks a design family deterministically from the outline, so
      // the same approved outline gives the same deck.
      const deck = await post('mapping', { outline, family_id: null });
      const built = (await post('build', { deck })) as Built;
      onGenerated(built);
      setPhase('idle');
      setOutline(null);
    } catch (err) {
      setError((err as Error).message);
      setPhase('outline');
    }
  }

  return (
    <div className="generate-panel" data-generate-panel>
      <div className="generate-panel__form">
        <label>
          Topic
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="What the deck is about"
          />
        </label>
        <label>
          Slides
          <input
            type="number"
            min={1}
            max={40}
            value={slideCount}
            onChange={(e) => setSlideCount(Number(e.target.value))}
          />
        </label>
        <label>
          Audience
          <input value={audience} onChange={(e) => setAudience(e.target.value)} />
        </label>
        <label>
          Goal
          <input value={goal} onChange={(e) => setGoal(e.target.value)} />
        </label>
        <button
          onClick={handleInterview}
          disabled={topic.trim().length === 0 || phase === 'building'}
        >
          Generate outline
        </button>
      </div>

      {error && <div className="generate-panel__error">{error}</div>}

      {outline && (
        <div className="generate-panel__outline" data-outline>
          <h2>{outline.title}</h2>
          <p>
            {outline.audience} — {outline.goal}
          </p>
          {outline.sections.map((section) => (
            <div key={section.heading} className="generate-panel__section">
              <h3>{section.heading}</h3>
              <p>{section.summary}</p>
              <ul>
                {section.claims.map((claim) => (
                  // Provenance is the trust device: a claim the model invented
                  // is marked as such before any slide exists.
                  <li key={claim.text} data-claim-source={claim.source}>
                    <span className="generate-panel__source">
                      {claim.source === 'user' ? 'YOU' : 'AI'}
                    </span>{' '}
                    {claim.text}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div className="generate-panel__actions">
            <button onClick={handleApprove} disabled={phase === 'building'}>
              {phase === 'building' ? 'Building…' : 'Approve and build'}
            </button>
            <button
              className="generate-panel__reject"
              onClick={() => {
                setOutline(null);
                setPhase('idle');
              }}
              disabled={phase === 'building'}
            >
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
