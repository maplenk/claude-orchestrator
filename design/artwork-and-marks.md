# Artwork and provider marks — `Orchestrator Control Plane ink`

Every visual in the mockup is a labelled placeholder. This file says what goes in each
one, where to get it, and what the licence obliges you to do. Nothing here is decoration
for its own sake — the CSP blocks external images, so **whatever you pick has to be
inlined into `ui/dashboard.html`** as an inline `<svg>` or a `data:` URI.

---

## 1. The three artwork slots

| Slot | In the file | Size | What it wants |
| --- | --- | --- | --- |
| Sidebar column | bottom of the left rail | 240 × 200 | Vertical sumi-e: bamboo, a stone lantern, raked gravel. Cropped tall. |
| Hero wash | top right of the main column | 900 × 300 | Horizontal sumi-e: distant mountain, low sun, a blossom branch entering from the right. Must fade to nothing on the left so the headline stays readable. |
| Seal | beside the footer line | 34 × 34 | A square red *hanko*-style seal. Can be your own initials or the project name. |

### Where to get them

**Public domain, safest, best quality — museum open-access collections.**
These are scans of real ink paintings, released for any use including commercial:

- **The Metropolitan Museum of Art — Open Access** (`metmuseum.org/art/collection`, filter
  "Open Access"). Search *sumi-e*, *Japanese ink painting*, *Kanō school*, *Sesshū*.
  CC0 — no attribution required.
- **Smithsonian Open Access** (`si.edu/openaccess`) — Freer Gallery of Art holds a deep
  Japanese and Chinese ink collection. CC0.
- **Rijksmuseum Studio** (`rijksmuseum.nl/en/rijksstudio`) — very high-resolution
  downloads, strong ukiyo-e and ink holdings. Public domain.
- **Art Institute of Chicago** (`artic.edu/collection`, "Public domain" filter) — clean
  API if you want to script the fetch.
- **Library of Congress — Japanese prints** (`loc.gov`) — public domain scans.

**Generated or drawn to order** (if you want the exact composition above):

- Commission on a marketplace — a sumi-e artist will supply SVG or transparent PNG for a
  one-off fee. Ask explicitly for **commercial use and modification rights in writing**.
- Generate with an image model, then trace to SVG. Check your model's terms: some grant
  full commercial rights, some do not, and outputs may not be copyrightable at all in
  some jurisdictions — which cuts both ways.

**Do not** pull from Pinterest, Google Images, or a stock site's watermarked preview.
Those are the three routes that end in a takedown.

### Getting them into a CSP-locked single file

1. Prefer **SVG**: an ink wash traces well to a few paths, stays sharp on any display, and
   inlines as markup with no encoding step.
2. Otherwise export **WebP or PNG at 2×**, run it through an optimiser, then inline as
   `background-image:url("data:image/webp;base64,…")`. Keep each under ~80 KB — the whole
   dashboard is one file served off localhost, but it still has to parse.
3. Give the hero a **transparent left edge** (or a CSS `mask-image` fade) rather than
   baking the paper colour in, so it works in both light and dark mode.
4. Both washes are decorative: mark them `aria-hidden="true"` and give the seal an
   `aria-label` if it carries the project name.

---

## 2. Provider marks (the 34 × 34 squares in Harnesses)

Four slots, one per harness. Each currently shows a mono letter placeholder.

| Harness | Mark | Where the official asset lives |
| --- | --- | --- |
| `claude` | Anthropic | Anthropic brand/press resources — `anthropic.com` |
| `codex` | OpenAI | OpenAI brand guidelines — `openai.com/brand` |
| `grok` | xAI | `x.ai` press/brand assets |
| `pi` | pi coding agent | the `@earendil-works/pi-coding-agent` package repository |

**Always take the vendor's own SVG from their brand page.** Never redraw a logo by hand
and never use a third-party icon set's copy of it — both produce a subtly wrong mark,
which is worse than no mark.

### Trademark reality, before you ship

These are trademarks, not just images, and the rules differ from copyright:

- **Nominative use is generally fine.** Naming a model you interoperate with, and showing
  its mark to identify it, is normal and defensible — that is exactly what this dashboard
  does.
- **Do not imply endorsement, affiliation or partnership.** No vendor logo in your own
  masthead, product name, favicon, or marketing hero. Inside a "which model runs this
  role" table is the right place.
- **Follow each vendor's brand guidelines**: minimum size, clear space, no recolouring, no
  stretching, no adding effects, no putting the mark inside your own shape or badge.
  Several explicitly forbid the rounded-square treatment the reference screenshot uses —
  check before you adopt it. If a vendor's guidelines conflict with the placeholder
  geometry, the guidelines win and I'll adjust the layout.
- **Keep the marks equal in weight.** Sizing one larger, or giving one colour and the rest
  grey, reads as a partnership claim.
- Some brand pages require a licence request for any use at all. If in doubt, the
  wordmark in plain text (`claude`, `codex`, `grok`, `pi`) is always safe — the design
  already reads fine without the squares.

### Suggested `TRADEMARKS.md` for the repo

```
# Trademarks

Claude and Anthropic are trademarks of Anthropic PBC.
OpenAI and Codex are trademarks of OpenAI.
Grok and xAI are trademarks of X.AI Corp.
Other product names are the trademarks of their respective owners.

This project is an independent, unaffiliated tool. Marks are used
nominatively, to identify the models a role can be delegated to.
No endorsement, sponsorship or affiliation is claimed or implied.
Each mark is reproduced from its owner's official brand assets and
used according to that owner's brand guidelines.
```

Add a one-line pointer to it from `README.md`, and repeat the "independent and
unaffiliated" sentence in the dashboard footer if you ever publish screenshots.

---

## 3. If you would rather ship no imagery

The layout holds without any of it — drop the two wash slots and the marks, and the
harness rows fall back to the letter squares. Worth knowing that the calm in the
reference screenshot comes mostly from the paper colour, the whitespace and the type,
not from the mountain.
