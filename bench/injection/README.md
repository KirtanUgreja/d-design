Hostile pasted material, interview answers, prompts and search results. Each
case is a v4 `Brief` with one payload, plus `must_not_contain`: strings that
must appear in no field of the storyline the content stages produce.

Cases 01–07 are recovered from v3's `api/evals/injection/` (`git show
cbfebfa^:api/evals/injection/`) and reshaped for the v4 `Brief`. Case 08 is
new: a search result that addresses the model. The eval is
`cli bench injection`; the threshold is 0 cases that change the output
channel (docs/v4/content.md -> Evals).
