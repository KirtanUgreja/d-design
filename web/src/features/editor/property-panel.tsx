'use client';

// The panel renders whatever `controls.ts` derived from the schema. It knows
// no block types, and adding a prop to the Pydantic model makes a control
// appear here without this file being touched — which is the whole point
// (docs/v1/plan/09-editor.md -> "The panel is generated, not written").
//
// Tailwind, because this is app chrome. The panel is explicitly the cold 90%
// (docs/coderules/performance.md): assemble it, do not craft it. The one thing
// here that *is* designed is `StylingAnswer` at the bottom, and that is the
// most-read sentence the product will ship.

import { useState } from 'react';

import type { Block, BlockPatch } from '@/schema';

import { CONTROLS, type Control } from './controls';

const LABEL = 'text-xs font-medium tracking-wide text-neutral-400 uppercase';
const INPUT =
  'w-full rounded-md border border-neutral-800 bg-neutral-950 px-2.5 py-1.5 text-sm ' +
  'text-neutral-100 focus:border-neutral-600 focus:outline-none';

export function PropertyPanel({
  block,
  sceneId,
  onPatch,
  onReachForStyling,
  error,
}: {
  block: Block;
  sceneId: string;
  onPatch: (patch: BlockPatch) => void;
  /** Fires when someone goes looking for a styling control. The cheapest
   * high-signal metric in the product, and the number that says whether the
   * answer below is working (docs/v1/plan/09-editor.md). */
  onReachForStyling: () => void;
  error: string | null;
}) {
  const controls = CONTROLS[block.props.type] ?? [];
  const props: Record<string, unknown> = block.props;

  function set(name: string, value: unknown) {
    onPatch({ sceneId, blockId: block.id, props: { [name]: value } });
  }

  return (
    <aside className="w-72 shrink-0 space-y-4 border-l border-neutral-800 bg-neutral-900/40 p-4">
      <header>
        <h2 className="text-sm font-semibold text-neutral-100">{block.props.type}</h2>
        <p className="text-xs text-neutral-500">{block.id}</p>
      </header>

      {controls.map((control) => (
        <ControlField
          key={control.name}
          control={control}
          value={props[control.name]}
          onChange={(value) => set(control.name, value)}
        />
      ))}

      {/* ponytail: no `motion` control, and the reason is the patch shape
          rather than the panel. `motion` lives on `Block`, not on `props`, and
          `BlockPatch` carries `props` only — so offering it here would mean
          widening the one shape both producers share, which is this phase's
          central invariant and not a decision to make from inside a panel.
          The scene-schema doc does list `motion` as editable, so this is owed.
          Upgrade: add `motion?` to `BlockPatch` in `api/schema/patch.py`,
          regenerate, and handle it in `applyPatch` beside `props` — both
          producers keep one shape, which is the property that matters. */}

      {error && (
        <p role="alert" className="text-xs text-red-400">
          {error}
        </p>
      )}

      <StylingAnswer onReach={onReachForStyling} />
    </aside>
  );
}

function ControlField({
  control,
  value,
  onChange,
}: {
  control: Control;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (control.kind === 'readonly') {
    return (
      <div>
        <span className={LABEL}>{control.name}</span>
        <p className="mt-1 text-xs text-neutral-500">
          Generated code, not hand-edited here. Describe the change instead.
        </p>
      </div>
    );
  }

  if (control.kind === 'reroll') {
    // A seed is a number with no meaning, so a number field invites someone to
    // reason about a value that cannot be reasoned about. Same action, minus
    // the arithmetic — and the affordance users reach for constantly.
    return (
      <div>
        <span className={LABEL}>visual</span>
        <button
          type="button"
          className="mt-1.5 w-full rounded-md border border-neutral-700 px-2.5 py-1.5 text-sm text-neutral-200 hover:border-neutral-500"
          onClick={() => onChange(Math.floor(Math.random() * 2147483647))}
        >
          Reroll
        </button>
      </div>
    );
  }

  if (control.kind === 'boolean') {
    return (
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={value === true}
          aria-label={control.name}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="text-sm text-neutral-300">{control.name}</span>
      </label>
    );
  }

  if (control.kind === 'choice') {
    return (
      <label className="block">
        <span className={LABEL}>{control.name}</span>
        <select
          className={`${INPUT} mt-1.5`}
          value={typeof value === 'string' ? value : ''}
          aria-label={control.name}
          onChange={(e) => onChange(e.target.value === '' ? null : e.target.value)}
        >
          {control.optional && <option value="">(default)</option>}
          {control.options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
    );
  }

  const text = typeof value === 'string' ? value : '';
  return (
    <label className="block">
      <span className={LABEL}>{control.name}</span>
      {control.multiline ? (
        <textarea
          className={`${INPUT} mt-1.5 resize-y`}
          rows={3}
          value={text}
          maxLength={control.maxLength ?? undefined}
          aria-label={control.name}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className={`${INPUT} mt-1.5`}
          value={text}
          maxLength={control.maxLength ?? undefined}
          aria-label={control.name}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
      {control.maxLength !== null && (
        <span className="mt-1 block text-right text-xs text-neutral-600">
          {text.length}/{control.maxLength}
        </span>
      )}
    </label>
  );
}

/** The designed absence (docs/v1/plan/09-editor.md -> "Design the absence,
 * because the absence is the product").
 *
 * The panel cannot offer a colour picker — not hidden, unrepresentable — and
 * that distinction is invisible to someone who just wants the headline
 * smaller. Undesigned, it is a bug report; designed, it is the pitch. So the
 * answer sits inline, once, positively, in the place the control was expected,
 * rather than in a docs page nobody opens before churning.
 *
 * The replacements are named because they are genuinely more powerful than
 * what they replace, and saying so is the argument.
 */
function StylingAnswer({ onReach }: { onReach: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-neutral-800 pt-3">
      <button
        type="button"
        className="text-xs text-neutral-400 underline underline-offset-2 hover:text-neutral-200"
        onClick={() => {
          setOpen((o) => !o);
          if (!open) onReach();
        }}
      >
        Looking for colours, fonts or size?
      </button>
      {open && (
        <div className="mt-2 space-y-2 text-xs text-neutral-400">
          <p className="text-neutral-300">
            There are none, and that is the feature — you cannot make this ugly.
          </p>
          <p>
            Type, colour, spacing and motion come from the art direction, so every scene
            stays in one system however much you edit the words.
          </p>
          <ul className="space-y-1 text-neutral-500">
            <li>
              Want a headline to hit harder? Set{' '}
              <b className="text-neutral-300">emphasis</b> to{' '}
              <b className="text-neutral-300">hero</b>.
            </li>
            <li>
              Want different colours? That is the{' '}
              <b className="text-neutral-300">brand kit</b> — it restyles everything at
              once.
            </li>
            <li>
              Want a different look for the background?{' '}
              <b className="text-neutral-300">Reroll</b>.
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
