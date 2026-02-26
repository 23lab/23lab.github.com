# AGENTS.md

## Cursor Cloud specific instructions

This repository is a **static blog** (pre-built Hexo output deployed via GitHub Pages). It contains only HTML, CSS, JS, and image assets — there is no build system, no `package.json`, no dependencies to install, and no linting/testing configuration.

### Running the blog locally

Serve the static files from the repo root with any static file server:

```bash
serve -l 3000 .
```

Or alternatively: `python3 -m http.server 3000`

The blog will be available at `http://localhost:3000/`.

### Key notes

- The `CNAME` file points to `blog.23lab.com` (GitHub Pages custom domain).
- Blog posts are organized by date in directories like `2017/05/28/post-slug/index.html`.
- The `/archives/` page lists all posts by year.
- There is no source code (Markdown, Hexo config, theme) in this repo — only the generated output.
- No lint, test, or build commands exist for this repository.
