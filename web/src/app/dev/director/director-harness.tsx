'use client';

// Standing judgment surface for the Director -> approve -> Build loop
// (docs/v1/plan/07-director.md), the same role dev/primitives plays for
// the renderer. Not part of the published artifact — dev-only, ordinary
// app chrome is fair game. Brief is hardcoded rather than read from a real
// Intake screen because Intake is phase 08 and does not exist yet; this
// harness exists so the loop is exercisable against the real API before
// that screen does.

import { useState } from 'react';

import { directBrief, OutlineEditor } from '@/features/director';
import { streamBuild, type GenerationEvent } from '@/features/generation';
import type { Brief, Outline } from '@/schema';

const SAMPLE_BRIEF: Brief = {
  goal: 'Launch a project-management tool built for small design teams',
  audience: 'Design leads at 5-30 person product teams',
  keyMessages: [
    'One board that replaces the spreadsheet, the deck, and the group chat',
    'Built around design review, not ticket status',
    'Set up in an afternoon, not a quarter',
  ],
  proofPoints: ['cuts review cycles from days to hours in early customer teams'],
  tone: 'confident, plainspoken',
  cta: { label: 'Start a free trial', href: 'https://example.com/trial' },
  assets: [],
};

export function DirectorHarness() {
  const [experienceId] = useState(() => crypto.randomUUID());
  const [outline, setOutline] = useState<Outline | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [events, setEvents] = useState<GenerationEvent[]>([]);
  const [status, setStatus] = useState('idle');

  async function runDirector() {
    setRegenerating(true);
    setStatus('calling Director…');
    const result = await directBrief(experienceId, SAMPLE_BRIEF);
    setRegenerating(false);
    if (result.ok) {
      setOutline(result.value);
      setStatus('outline ready');
    } else {
      setStatus(`Director failed: ${result.error.code} ${result.error.message}`);
    }
  }

  async function runBuild(approved: Outline) {
    setEvents([]);
    setStatus('building…');
    for await (const event of streamBuild(experienceId, {
      brief: SAMPLE_BRIEF,
      outline: approved,
    })) {
      setEvents((prev) => [...prev, event]);
    }
    setStatus('build complete');
  }

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1>Director harness</h1>
      <p>{status}</p>

      {!outline && (
        <button type="button" onClick={runDirector} disabled={regenerating}>
          {regenerating ? 'Calling Director…' : 'Generate outline'}
        </button>
      )}

      {outline && (
        <OutlineEditor
          initial={outline}
          onApprove={runBuild}
          onRegenerate={runDirector}
          regenerating={regenerating}
        />
      )}

      <pre>{JSON.stringify(events, null, 2)}</pre>
    </div>
  );
}
