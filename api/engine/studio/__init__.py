"""The studio (2026-10-09): the engine that writes and designs a deck, in four
layers, each a strong model with one job (owner: "make layers like one for
research, one for the outline, one for designing and one for improving it").

1. ``research``: what the product is and the evidence around it, verified.
2. ``outline``: the argument, slide by slide, every number traced.
3. ``direct`` then ``design``: an art director plans every slide's composition
   for the whole deck at once; a designer writes each slide in HTML, CSS and
   flat SVG, free of templates.
4. ``improve``: a critic looks at each rendered slide and redesigns it.

Around them, unchanged: the sanitizer and lint on every answer, Chromium QA
on every slide, a targeted repair, and a code-built layout as the floor.
``build`` runs it all; nothing here reads the environment or a web framework.
"""
