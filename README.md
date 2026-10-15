# theodorewalrond.com

Static site for theodorewalrond.com, served by GitHub Pages from `/docs`.

- `python3 build.py` builds a preview (noindex) into `docs/`
- `python3 build.py --live` builds the production site (indexable, adds `CNAME`)

Content lives in `build.py` (pages) and `src/posts.json` (blog posts). Photos sit in
`src/wp-content/uploads/` at the same paths the old WordPress site used, so
existing image URLs keep working. Retired WordPress URLs redirect via small
meta-refresh pages (see `REDIRECTS` in `build.py`).
