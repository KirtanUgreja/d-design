#!/usr/bin/env node
// Schema codegen: api/schema (Pydantic) -> JSON Schema -> TypeScript types + Zod validator.
//
// The Pydantic schema is the source of truth. This script calls the Python
// side to emit the JSON Schema for Deck, Outline, Brief, and the registry
// shapes, then writes generated TypeScript into web/src/schema/generated/.
//
// The generated output is NEVER hand-edited. It carries a header saying so,
// and the pre-commit gate runs this with --check and fails if the committed
// output differs from what regenerating produces (coderules/python.md rule 1).
//
// Generation strategy: the schema is a tree of $refs into a $defs table
// (Pydantic emits each model once, in the root $defs). This script merges all
// reachable $defs, resolves every $ref to a named Zod schema, and emits each
// named schema once followed by the root. An anyOf whose branches all carry a
// literal `kind` becomes z.discriminatedUnion; a plain anyOf stays z.union.

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const check = process.argv.includes('--check');
const here = dirname(fileURLToPath(import.meta.url));
const webRoot = join(here, '..');
const apiRoot = join(webRoot, '..', 'api');
const outDir = join(webRoot, 'src', 'schema', 'generated');

// Format the emitted file with prettier so regeneration is always
// prettier-clean (the gate runs prettier --check over web/, generated
// included). This also runs in --check mode to catch a formatter version drift.
function prettierFormat(source) {
  return execFileSync(
    join(webRoot, 'node_modules', '.bin', 'prettier'),
    ['--stdin-filepath', 'deck.ts', '--parser', 'typescript'],
    { input: source, encoding: 'utf8' },
  );
}

const HEADER = `/**
 * GENERATED FILE — do not hand-edit.
 *
 * Source of truth: api/schema/*.py (Pydantic). Regenerate with
 * \`pnpm schema:generate\`. A hand-edit here fails the gate
 * (docs/coderules/python.md -> "Generated TypeScript is never hand-edited").
 */
`;

const shapes = ['Deck', 'Outline', 'Brief'];

function pythonJsonSchema(shape) {
  const script = `
import json
from schema.${shape === 'Deck' ? 'deck' : 'outline'} import ${shape}
print(json.dumps(${shape}.model_json_schema()))
`;
  const out = execFileSync('uv', ['run', 'python', '-c', script], {
    cwd: apiRoot,
    encoding: 'utf8',
  });
  return JSON.parse(out.trim());
}

function refName(ref) {
  return ref.split('/').pop();
}

// Collect every $defs table reachable from the root, merged under one namespace.
function collectDefs(schema, defs = {}) {
  if (schema.$defs) {
    for (const [k, v] of Object.entries(schema.$defs)) {
      if (!(k in defs)) {
        defs[k] = v;
        collectDefs(v, defs);
      }
    }
  }
  if (schema.properties) for (const v of Object.values(schema.properties)) collectDefs(v, defs);
  if (schema.items) collectDefs(schema.items, defs);
  if (schema.anyOf) for (const v of schema.anyOf) collectDefs(v, defs);
  if (schema.oneOf) for (const v of schema.oneOf) collectDefs(v, defs);
  return defs;
}

// Does every branch of this anyOf/oneOf carry a literal `kind` discriminator?
function isDiscriminated(schema) {
  const branches = schema.anyOf || schema.oneOf || [];
  if (branches.length === 0) return false;
  return branches.every((b) => b.$ref !== undefined && b.anyOf === undefined);
}

function zodFromJsonSchema(schema, defs, indent = 0) {
  const pad = '  '.repeat(indent);
  const pad1 = '  '.repeat(indent + 1);

  if (!schema) throw new Error(`zodFromJsonSchema got undefined schema at indent ${indent}`);

  if (schema.$ref) return `${refName(schema.$ref)}Schema`;

  if (schema.anyOf || schema.oneOf) {
    if (isDiscriminated(schema)) {
      const variants = (schema.anyOf || schema.oneOf)
        .map((s) => zodFromJsonSchema(s, defs, indent + 1))
        .join(`,\n${pad1}`);
      return `z.discriminatedUnion('kind', [\n${pad1}${variants}\n${pad}])`;
    }
    const variants = (schema.anyOf || schema.oneOf)
      .map((s) => zodFromJsonSchema(s, defs, indent + 1))
      .join(`,\n${pad1}`);
    return `z.union([\n${pad1}${variants}\n${pad}])`;
  }

  switch (schema.type) {
    case 'string':
      if (schema.const !== undefined) return `z.literal(${JSON.stringify(schema.const)})`;
      if (schema.enum) {
        const vals = schema.enum.map((v) => `z.literal(${JSON.stringify(v)})`).join(', ');
        return `z.union([${vals}])`;
      }
      return `z.string()${schema.minLength ? `.min(${schema.minLength})` : ''}${schema.maxLength ? `.max(${schema.maxLength})` : ''}${schema.pattern ? `.regex(/${schema.pattern}/)` : ''}`;
    case 'integer':
    case 'number':
      if (schema.const !== undefined) return `z.literal(${schema.const})`;
      return `z.number()${schema.minimum !== undefined ? `.min(${schema.minimum})` : ''}${schema.maximum !== undefined ? `.max(${schema.maximum})` : ''}`;
    case 'boolean':
      return 'z.boolean()';
    case 'null':
      return 'z.null()';
    case 'array':
      if (schema.prefixItems) {
        // Pydantic tuple -> JSON Schema prefixItems -> z.tuple
        const items = schema.prefixItems
          .map((s) => zodFromJsonSchema(s, defs, indent + 1))
          .join(',\n' + pad1);
        return `z.tuple([\n${pad1}${items}\n${pad}])`;
      }
      return `z.array(${zodFromJsonSchema(schema.items, defs, indent)})${schema.minItems ? `.min(${schema.minItems})` : ''}${schema.maxItems ? `.max(${schema.maxItems})` : ''}`;
    case 'object':
    default: {
      const required = new Set(schema.required || []);
      const props = Object.entries(schema.properties || {})
        .map(([key, sub]) => {
          const child = zodFromJsonSchema(sub, defs, indent + 1);
          const opt = required.has(key) ? '' : '.optional()';
          return `${pad1}${JSON.stringify(key)}: ${child}${opt},`;
        })
        .join('\n');
      return `z.object({\n${props}\n${pad}})`;
    }
  }
}

// Emit named schemas in dependency order so a `const XSchema = ...` that
// references `YSchema` is declared after Y. JavaScript const is TDZ-hoisted, so
// a reference before declaration throws at module load — exactly the bug that
// ordering by insertion order produced (Slide referenced TextBlock which came
// later).
function refsIn(def, defs) {
  const refs = new Set();
  const walk = (s) => {
    if (!s) return;
    if (s.$ref) refs.add(refName(s.$ref));
    if (s.properties) for (const v of Object.values(s.properties)) walk(v);
    if (s.items) walk(s.items);
    if (s.anyOf) for (const v of s.anyOf) walk(v);
    if (s.oneOf) for (const v of s.oneOf) walk(v);
  };
  walk(def);
  return [...refs].filter((r) => r in defs);
}

function emit(shape) {
  const root = pythonJsonSchema(shape);
  const defs = collectDefs(root);

  // Topological order via DFS (post-order: dependencies first).
  const ordered = [];
  const visiting = new Set();
  const visited = new Set();
  const visit = (name) => {
    if (visited.has(name)) return;
    if (visiting.has(name)) return; // cycle guard; not expected here
    visiting.add(name);
    for (const dep of refsIn(defs[name], defs)) visit(dep);
    visiting.delete(name);
    visited.add(name);
    ordered.push(name);
  };
  for (const name of Object.keys(defs)) visit(name);

  const parts = [];
  for (const name of ordered) {
    parts.push(`const ${name}Schema = ${zodFromJsonSchema(defs[name], defs)};`);
  }
  parts.push(`export const ${shape}Schema = ${zodFromJsonSchema(root, defs)};`);
  parts.push(`export type ${shape} = z.infer<typeof ${shape}Schema>;`);

  return prettierFormat(`${HEADER}import { z } from 'zod';\n\n${parts.join('\n\n')}\n`);
}

let changed = false;
mkdirSync(outDir, { recursive: true });
for (const shape of shapes) {
  const body = emit(shape);
  const file = join(outDir, `${shape}.ts`);
  if (existsSync(file) && readFileSync(file, 'utf8') === body) continue;
  changed = true;
  if (!check) writeFileSync(file, body);
}

if (check) process.exit(changed ? 1 : 0);
console.log(changed ? `generated ${shapes.length} schema files` : 'schema unchanged');
