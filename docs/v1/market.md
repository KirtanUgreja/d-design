# Market Reality

Researched August 2026. This document exists because the v1 spec makes claims about competitors, and those claims should be grounded in what actually happened to them.

## The category has one clear winner and one clear casualty

**Gamma** — ~$100M ARR (Oct 2025), $2.1B valuation, ~70M users, ~600K paying subscribers, **profitable since 2023**, ~50 employees, and only ~$23M raised before its Series B. It now positions explicitly as "replacing PowerPoint for the AI era."

**Tome** — raised heavily, hit ~$4M ARR, cut most of its 70-person team in Oct 2024, sunset Tome Slides on **30 April 2025**, and pivoted into sales automation as Lightfield.

Same category. Same technology wave. Opposite outcomes. The difference is the most useful thing in this document.

## Why Tome died

From the post-mortems and the founder's own account:

| Cause | Detail |
|---|---|
| **Wrong users** | Attracted Gen Z, students, freelancers, artists — people who loved it and would not pay. Tome reached millions of users and ~$4M ARR. |
| **Positioning too broad** | Aimed at "anyone who wants to tell a compelling story." The company's own retrospective: *"Building AI for everyone at once is fundamentally flawed."* |
| **Storytelling isn't a must-have** | The specific finding: storytelling is valuable, but businesses don't treat it as essential. Beauty didn't convert. |
| **The cruelest detail** | Tome's most engaged users were **sales and growth professionals** — precisely the segment Gamma deliberately targeted from day one. Tome had the right users and the wrong aim. |

Gamma, by contrast, targeted professionals and knowledge workers needing workplace output, stayed model-agnostic rather than building its own models, and focused spend on UX.

## What this means for this product

**It validates the wedge decision.** Choosing marketers doing product launches — a specific role, with budget, where output quality maps to money — is the correction Tome made two years too late. Do not widen it. The pull toward "anyone who presents" is exactly the failure mode that killed a well-funded competitor.

**It challenges the framing.** This product's origin document says *"enabling anyone to communicate complex ideas."* That sentence is Tome's thesis almost verbatim, and Tome disproved it commercially. The vision can stay; the go-to-market cannot be built on it.

**It sharpens the "why not Gamma" answer.** Gamma won the mainstream deck market decisively — head-on competition there is unwinnable. But Gamma is explicitly weak where this product is strong: its own reviews cite generic AI phrasing needing manual refinement, and design customization "limited compared to PowerPoint or Keynote for pixel-level control." The gap is *creative ceiling*, not speed.

**It reframes the competitive set.** With URL + embed delivery and a marketer wedge, the real comparison set is Framer, Vev, Readymag, and Webflow — not Gamma or PowerPoint. See the positioning risk in [spec.md](spec.md).

## The uncomfortable question

Gamma reached $100M ARR with ~50 people by making presentations *faster*. This product bets that people will pay for presentations that are *better*.

Tome bet the same thing and lost.

The distinction that makes this bet different is the wedge: Tome sold beauty to students; this sells conversion-relevant launch experiences to marketers with campaign budgets, delivered as a URL that can be measured. That difference has to be real, not rhetorical — and it is testable the first day a marketer sees it. The bets tables in `../v2/spec.md` and `../v3/spec.md` are where that gets checked.

## Sources

- [How Gamma grew to $100M ARR (and a $2.1B valuation)](https://thegtmnewsletter.substack.com/p/how-gamma-grew-to-100m-arr-and-a)
- [Gamma Surpasses $100M ARR, Raises at $2.1B Valuation](https://www.businesswire.com/news/home/20251110805751/en/Gamma-Surpasses-$100M-ARR-Raises-at-$2.1B-Valuation-as-It-Replaces-PowerPoint-for-the-AI-Era)
- [Tome Failed in AI PPT — Why Is Gamma Thriving?](https://readthesignal.co/p/tome-failed-in-ai-pptwhy-is-gamma)
- [Why Tome.app Pivoted Away from Presentations](https://autoppt.com/blog/tome-app-pivot-away-from-presentations/)
- [What Happened to Tome AI? Shutdown Timeline](https://deckary.com/blog/tome-review)
- [The Best AI Presentation Tools of 2026 — comparison](https://www.slidegmm.ai/en/blog/ai-presentation-tools-comparison-2026)
