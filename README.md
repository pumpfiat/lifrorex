# Liforex

A free, gamified forex-learning site — puzzles, lessons, tools, and a
practice mode. Plain HTML/CSS/JS. No build step, no framework, no backend.
Content lives in `data/*.json` so you can add material without touching code.

This version merges two things:
- The improved page structure and layout (compact top nav with active-tab
  underline, homepage hero + stats row, puzzle-with-sidebar layout, minimal
  one-line footer) from a hand-built draft
- A **light theme** using lila's real light-theme color values (decoded from
  the actual `ui.zip` source), replacing that draft's dark theme

## Two real bugs fixed in this merge

1. **Nav active-tab highlighting was broken.** `main.js` looked for
   `nav.main-nav`, but the actual header markup uses `nav.site-nav` — so the
   blue underline under the current page never appeared. Fixed.
2. **Decision buttons didn't work at all.** `puzzles.js` and `practice.js`
   attached click handlers to `.decision-btn`, but the actual buttons are
   classed `.choice` — meaning clicking BUY/SELL/WAIT did nothing. Fixed.

Worth testing locally (Live Server) before assuming any future edits work —
these are the kind of bugs that are invisible just from reading the code.

## License

AGPL-3.0 — see `LICENSE` (replace the placeholder with GitHub's real
generated text before publishing) and `ATTRIBUTION.md` for exactly what was
taken from lila's source and what wasn't.

## Project structure

```
liforex-final/
├── index.html, learn.html, practice.html, community.html, tools.html
├── css/style.css       Light theme, real lila color/shadow/radius values
├── js/
│   ├── main.js           Nav highlighting + rating display
│   ├── puzzles.js          Puzzle page logic
│   ├── practice.js          Streak mode logic
│   ├── learn.js               Learn page logic
│   ├── community.js            Leaderboard logic
│   └── tools.js                  Calculator logic
└── data/
    ├── puzzles.json                Puzzle content — add more here
    └── lessons.json                 Lesson content — add more here
```

## Running locally

Because pages load `data/*.json` with `fetch()`, double-clicking `index.html`
won't work (browsers block local file fetches). Use VS Code's Live Server
extension, or run `python3 -m http.server 8000` in this folder and open
`http://localhost:8000`.

## Deploying on GitHub Pages

1. Create a GitHub repo, add the **AGPL-3.0** license when prompted.
2. `git init && git add . && git commit -m "Liforex" && git branch -M main`
   `git remote add origin <your-repo-url> && git push -u origin main`
3. Repo Settings → Pages → Source: "Deploy from a branch", `main`, `/ (root)`.
4. Live at `https://YOUR-USERNAME.github.io/liforex/` within a minute or two.
