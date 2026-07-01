# rshiri.github.io - Ram Shiri's portfolio

A single-page personal portfolio (data science in sports). Static HTML/CSS/JS - no build step,
no dependencies. Published with **GitHub Pages** at <https://rshiri.github.io/>.

## Files
| File | Purpose |
| --- | --- |
| `index.html` | The whole page (nav, hero, about, skills, projects, passions, contact) |
| `styles.css` | Fresh light brand - Space Grotesk + Inter, indigo→cyan accent |
| `main.js` | Nav, scroll-reveal, animated skill bars, scrollspy, contact-form logic |
| `assets/` | Favicon, CV PDF, project screenshots, OG image |

## Before you go live - 4 quick edits
1. **LinkedIn** - open `main.js`, set `CONFIG.LINKEDIN_URL` to your profile URL.
2. **Contact form** - create a free form at [formspree.io](https://formspree.io), then replace
   `XXXXXXX` in the `<form action="https://formspree.io/f/XXXXXXX">` tag in `index.html`.
   Until then the form politely falls back to opening your email client.
3. **CV** - replace `assets/Ram_Shiri_CV.pdf` with your real CV (keep the filename).
4. **Screenshots** - the three images in `assets/img/` (`bcn.png`, `nba.png`, `wc2026.png`) can be
   re-captured any time; if an image is missing the card shows a styled gradient fallback.

## Run locally
Any static server works, e.g.:
```
python -m http.server 8000
```
then open <http://localhost:8000>.

## Deploy
This repo is a **GitHub user site** (`rshiri.github.io`), so GitHub Pages serves the `main`
branch root automatically - just push. No Actions workflow or `gh-pages` branch needed.
