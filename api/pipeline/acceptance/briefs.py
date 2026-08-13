"""Golden briefs — the acceptance-run dataset (plan/08).

5-10 real briefs that exercise different topics, lengths, and image needs: a
product launch (wants a hero), a fundraising ask, a sales pitch, an internal
all-hands, and a conference talk. These are the eval dataset — checked in,
versioned, and run through the whole pipeline on the acceptance run.

A brief is what a user types: topic, slide count, audience, goal, brand kit
(typed text), and extra info. The interview turns it into an outline; the
pipeline turns the outline into a deck.
"""

from __future__ import annotations

from schema.outline import BrandKit, Brief

GOLDEN_BRIEFS: tuple[Brief, ...] = (
    Brief(
        topic="Launching a CRM for agencies that tracks clients, scope and billing",
        slide_count=8,
        audience="Agency founders and operations leads",
        goal="Get 20 pilot signups from the launch deck",
        brand_kit=BrandKit(
            colors="warm neutrals and one terracotta accent",
            fonts="serif display with sans body",
            vibe="editorial, calm, confident",
        ),
        extra_info="We already have three named customers and a waitlist of 40.",
    ),
    Brief(
        topic="Series A fundraising round for a developer-tools company",
        slide_count=12,
        audience="Venture investors",
        goal="Close the round at a $40M valuation",
        brand_kit=BrandKit(
            colors="deep navy with electric blue accent",
            fonts="geometric sans",
            vibe="precise, technical, ambitious",
        ),
        extra_info="$2.3M ARR, 92% gross margin, 41% month-over-month growth for six quarters.",
    ),
    Brief(
        topic="Sales pitch for an enterprise data platform",
        slide_count=10,
        audience="Chief Data Officers at F500 companies",
        goal="Book a proof-of-concept with three named accounts",
        brand_kit=BrandKit(
            colors="cool grey with one green accent",
            fonts="humanist sans",
            vibe="trustworthy, measurable",
        ),
        extra_info="The platform replaces a 6-month integration with a 3-week one.",
    ),
    Brief(
        topic="Internal all-hands: the company's Q3 priorities and reorg",
        slide_count=6,
        audience="The whole company, 120 people",
        goal="Everyone leaves knowing the three priorities and their team's part",
        brand_kit=BrandKit(
            colors="the company palette", fonts="the company type", vibe="direct, warm, no spin"
        ),
        extra_info="This is sensitive: no invented numbers, no hype, cite the CEO's memo.",
    ),
    Brief(
        topic="Conference talk: why offline-first software is a product moat",
        slide_count=9,
        audience="Software engineers and product leads",
        goal="A memorable talk that gets the audience to try offline-first patterns",
        brand_kit=BrandKit(
            colors="monochrome with one red accent",
            fonts="monospace for code, grotesk for prose",
            vibe="sharp, opinionated",
        ),
        extra_info="The talk has a demo of a file that works with the wifi cut.",
    ),
)
