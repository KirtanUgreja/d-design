"""The wall: every slide of every deck on one page, blind, for a human to score.

Automated gates cannot see design (docs/findings.md -> Process), so this page
is the gate at every phase exit. Labels are shuffled and anonymous; the key is
revealed only in the downloaded ratings file.
"""

from __future__ import annotations

import html
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path

CRITERIA = (
    ("D", "Designed"),
    ("S", "Says something"),
    ("V", "Varied"),
    ("X", "Distinct"),
    ("U", "Usable"),
)


@dataclass(frozen=True)
class WallDeck:
    system: str  # engine | oneshot | gamma | v3
    brief_id: str
    images: tuple[Path, ...]


def collect(root: Path, system: str) -> list[WallDeck]:
    """``root/<brief>/NN.png`` -> decks, or flat ``root/<brief>-NN.png``."""
    decks: list[WallDeck] = []
    if not root.is_dir():
        return decks
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        images = tuple(sorted(folder.glob("*.png")))
        if images:
            decks.append(WallDeck(system, folder.name, images))
    flat: dict[str, list[Path]] = {}
    for image in sorted(root.glob("*.png")):
        flat.setdefault(image.stem.rsplit("-", 1)[0], []).append(image)
    decks += [WallDeck(system, name, tuple(images)) for name, images in flat.items()]
    return decks


_PAGE = """<!doctype html><meta charset="utf-8"><title>Wall — __RUN__</title>
<style>
body{margin:0;padding:32px 40px 120px;background:#f6f4ef;color:#1b1a17;font:15px/1.4 Georgia,serif}
h1{font-size:22px;margin:0 0 4px} p.how{margin:0 0 28px;color:#6b675e;max-width:70ch}
.deck{border-top:1px solid #1b1a17;padding:18px 0 26px}
.head{display:flex;gap:28px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.label{font-size:20px;font-weight:700;min-width:90px}
.crit{display:flex;gap:4px;align-items:center}.crit span{margin-right:4px;color:#6b675e}
button{font:inherit;border:1px solid #1b1a17;background:none;width:30px;height:30px;cursor:pointer}
button.on{background:#1b1a17;color:#f6f4ef}
.defects button{width:auto;padding:0 10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:8px}
.grid img{width:100%;display:block;border:1px solid #d8d3c6;cursor:zoom-in}
#zoom{position:fixed;inset:0;background:#1b1a17ee;display:none;place-items:center;cursor:zoom-out}
#zoom img{max-width:96vw;max-height:96vh}
#bar{position:fixed;left:0;right:0;bottom:0;background:#1b1a17;color:#f6f4ef;padding:12px 40px;
display:flex;gap:24px;align-items:center}
#bar button{width:auto;padding:0 14px;border-color:#f6f4ef;color:#f6f4ef;height:34px}
</style>
<h1>Wall — __RUN__</h1>
<p class="how">Rate each deck 1 to 5 on the five criteria (bench/rubric.md) and count visible
defects. Labels are blind. Click a slide to enlarge. Ratings save in this browser; press
Download when done and put the file in this folder.</p>
<div id="decks"></div><div id="zoom"><img></div>
<div id="bar"><span id="progress"></span><button id="dl">Download ratings.json</button></div>
<script>
const DECKS=__DECKS__,CRIT=__CRIT__,KEY="wall:__RUN__";
const R=JSON.parse(localStorage.getItem(KEY)||"{}");
const save=()=>{localStorage.setItem(KEY,JSON.stringify(R));
  const done=DECKS.filter(d=>CRIT.every(c=>R[d.label]&&R[d.label][c[0]])).length;
  document.getElementById("progress").textContent=done+" of "+DECKS.length+" decks rated"};
const root=document.getElementById("decks");
for(const d of DECKS){R[d.label]=R[d.label]||{defects:0};
  const el=document.createElement("div");el.className="deck";
  const head=document.createElement("div");head.className="head";
  head.innerHTML='<span class="label">Deck '+d.label+'</span>';
  for(const [k,name] of CRIT){const c=document.createElement("span");c.className="crit";
    c.innerHTML="<span>"+name+"</span>";
    for(let n=1;n<=5;n++){const b=document.createElement("button");b.textContent=n;
      if(R[d.label][k]===n)b.className="on";
      b.onclick=()=>{R[d.label][k]=n;c.querySelectorAll("button").forEach(x=>x.className="");
        b.className="on";save()};c.appendChild(b)}
    head.appendChild(c)}
  const df=document.createElement("span");df.className="crit defects";
  const show=()=>df.querySelector("b").textContent=R[d.label].defects;
  df.innerHTML='<span>Defects</span><button>-</button> <b></b> <button>+</button>';
  const [minus,plus]=df.querySelectorAll("button");
  minus.onclick=()=>{R[d.label].defects=Math.max(0,R[d.label].defects-1);show();save()};
  plus.onclick=()=>{R[d.label].defects++;show();save()};
  head.appendChild(df);el.appendChild(head);show();
  const grid=document.createElement("div");grid.className="grid";
  for(const src of d.images){const i=document.createElement("img");i.src=src;i.loading="lazy";
    i.onclick=()=>{zoom.firstChild.src=src;zoom.style.display="grid"};grid.appendChild(i)}
  el.appendChild(grid);root.appendChild(el)}
const zoom=document.getElementById("zoom");zoom.onclick=()=>zoom.style.display="none";
document.getElementById("dl").onclick=()=>{
  const out=DECKS.map(d=>({system:d.system,brief:d.brief,label:d.label,...R[d.label]}));
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,2)],{type:"application/json"}));
  a.download="ratings.json";a.click()};
save();
</script>"""


def build(decks: list[WallDeck], out_file: Path, run: str, seed: int = 0) -> int:
    """Write the wall page. Image paths are relative to it. Returns the deck count."""
    order = list(decks)
    random.Random(seed).shuffle(order)  # noqa: S311 - a shuffle, not a secret
    payload = [
        {
            "label": f"{index + 1:02d}",
            "system": deck.system,
            "brief": deck.brief_id,
            "images": [os.path.relpath(image, out_file.parent) for image in deck.images],
        }
        for index, deck in enumerate(order)
    ]
    page = (
        _PAGE.replace("__RUN__", html.escape(run))
        .replace("__DECKS__", json.dumps(payload).replace("</", "<\\/"))
        .replace("__CRIT__", json.dumps(CRITERIA))
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(page)
    return len(payload)
