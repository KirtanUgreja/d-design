// The public surface of the schema. Hand-written; everything it re-exports is
// generated from api/schema/*.py and lives under ./generated, which nothing
// outside this file should import.
//
// ponytail: this folder has the layout a package would have. When `render`
// arrives in v2 there is a second TypeScript consumer, and publishing it as
// @d-design/schema is a package.json and a Changeset.

export {
  experienceSchema,
  type Experience,
  sceneSchema,
  type Scene,
  blockSchema,
  type Block,
  assetSchema,
  type Asset,
  brandKitSchema,
  type BrandKit,
  briefSchema,
  type Brief,
  interviewStepSchema,
  type InterviewStep,
  questionSchema,
  type Question,
  outlineSchema,
  type Outline,
  blockPatchSchema,
  type BlockPatch,
  editResultSchema,
  type EditResult,
  // The v2 art direction. `ArtDirectionRecord` is what `from-record.ts` turns
  // into tokens and what `render` receives instead of an id; `ArtDirectionRef`
  // is what an `Experience` carries and what resolves against the store.
  artDirectionRecordSchema,
  type ArtDirectionRecord,
  artDirectionRefSchema,
  type ArtDirectionRef,
  type ContentBudgets,
} from './generated/schema';
