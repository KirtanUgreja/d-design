#!/usr/bin/env node
// Schema codegen: api/schema (Pydantic) -> JSON Schema -> TypeScript types + Zod validator.
// Built in phase 01. This placeholder exists so the pre-commit gate has a real
// command to run; it currently emits nothing and --check trivially passes.
import { existsSync } from 'node:fs';

const check = process.argv.includes('--check');
if (!existsSync(new URL('../api/schema/deck.py', import.meta.url))) {
  process.exit(0); // no schema yet — nothing to generate, nothing to drift
}
if (check) {
  process.exit(0);
}
