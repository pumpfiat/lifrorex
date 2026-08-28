# Attribution

Liforex's visual design (not its forex content or puzzle logic) is derived
from lichess-org/lila (https://github.com/lichess-org/lila), specifically
from the `ui/` folder, and used under the terms of the GNU Affero General
Public License v3.0. This is why Liforex is licensed under AGPL-3.0 too —
that's a condition of using lila's code, not an optional choice.

## What was actually taken, and from where

**Color palette** (`css/style.css`, `:root` block) — decoded from the real
HSL custom properties in:
- `ui/lib/css/theme/_theme.light.scss` (light theme color tokens)
- `ui/lib/css/theme/_theme.default.scss` (tokens not overridden in light
  mode, e.g. the green/red "good"/"bad" colors, and the `---site-hue: 37deg`
  variable that gives lichess's backgrounds their warm cream tone even in
  light mode)

**Typography** — from `ui/lib/css/base/_typography.scss` and
`ui/lib/css/abstract/_extends.scss`: body text is 'Noto Sans', headings use
Roboto at font-weight 300.

**Card / box shadow** — the exact triple-layer box-shadow in `.card` is
copied from the `@mixin box-shadow` in `ui/lib/css/abstract/_mixins.scss`.

**Button shadow/gradient treatment** — `.choice` (buy/sell/wait) and
`.button.primary` use the exact color values `@mixin with-button-shadow`
produces for **light mode specifically** (lila's mixin has separate light
and dark parameters — an earlier draft of this file mistakenly used the dark
variant's numbers even in the light theme; this version corrects that),
computed from the real per-color values in
`ui/lib/css/component/_button.scss` (`.button-green`, `.button-red`, `.button`).

**Border radius** — `--radius: 7px` matches lila's real
`$box-radius-size: var(---ui-roundness, 7px)` in
`ui/lib/css/abstract/_variables.scss`.

**Neutral button / card-surface gradient** — the light "metal" gradient used
for `.button` and `.choice` buttons before hover is decoded from `%metal` in
`ui/lib/css/abstract/_extends.scss`, using the real `--c-metal-top` /
`--c-metal-bottom` light-theme values.

**Layout structure** (top nav with active-tab underline, homepage hero +
stats row, puzzle-with-sidebar layout, minimal single-line footer) — this
was built by the project owner as a hand-authored HTML/CSS layout inspired
by lila's visual language, not copied line-for-line from lila's actual
templates (which are Scala/Twirl, not portable HTML).

## What was NOT taken

- No chess-specific code (chessground, scalachess, puzzle-generation logic)
- No backend code, routing, or server logic — lila's frontend is tightly
  coupled to a Scala/Play/MongoDB backend that isn't reproduced here at all
- No forex content, puzzle data, or lesson content — all original to Liforex

## Note on the maintainer's stated preference

Lila's own README has historically asked people not to build a full public
clone of Lichess, preferring embedding via iframe instead, even though the
AGPL license permits broader reuse. Liforex is a different product in a
different domain (forex education, not chess), reusing design system
elements rather than the product itself — but this is worth being aware of
as a matter of respecting the project's spirit, separate from what the
license legally allows.
