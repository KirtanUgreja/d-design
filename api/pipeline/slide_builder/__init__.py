"""Slide builder — the heart of the pipeline.

One model call per slide, each with its own prompt carrying the design rules,
the layout archetype, and the chart shape. Generated images are a seam action
stored beside the deck as data URIs, inlined at export.
"""

from pipeline.slide_builder.slide_builder import BuildResult, run_build

__all__ = ["BuildResult", "run_build"]
