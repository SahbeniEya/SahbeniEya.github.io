# Eya Sahbeni — Portfolio

Static, single-page site. No build step, no backend, no frameworks, no tracking.

```
index.html                         the whole site (HTML + CSS + JS)
assets/cv/Eya_Sahbeni_CV.pdf       the CV linked from the hero, nav, contact and the `resume` command
assets/img/                        favicon, OG image, real CyberSmart screenshot and logo
repo-fixes/                        proposed GitHub changes — NOT applied; review them first
AUDIT_REPORT.md                    what changed and why
```

## Update the CV
Replace `assets/cv/Eya_Sahbeni_CV.pdf` and keep the same file name. All links use this relative path.

## Edit content
Projects, skills and the toolbox are arrays at the top of the `<script>` block
(`PROJECTS`, `SKILLS`, `TOOLBOX`). CyberSmart is the featured block inside the Projects section. Everything is rendered with `textContent`,
so pasting text there cannot inject HTML.

## Deploy (GitHub Pages)
1. Create a repository named `SahbeniEya.github.io`.
2. Upload `index.html` and the `assets/` folder (leave `repo-fixes/` and `AUDIT_REPORT.md` out if you like).
3. Settings → Pages → Deploy from branch → `main` / root.
4. After the first deploy, set `og:image` in `<head>` to the absolute URL
   `https://sahbenieya.github.io/assets/img/og-cover.jpg`.

## Local preview
Open `index.html`, or run `python3 -m http.server` in this folder and visit http://localhost:8000.
Fonts, tool icons and the GitHub "updated" dates need an internet connection; the page works without them.

## Hero character (eyes follow the cursor)
Built from your illustration without altering its appearance at rest:
- `avatar-base.webp/.jpg` — the illustration (cropped to head and shoulders) with the irises removed
- `avatar-iris-l.png`, `avatar-iris-r.png` — the original iris pixels, moved by JavaScript
- `avatar-closed-l.png`, `avatar-closed-r.png` — closed-eye frames shown during a short blink

The irises are clipped to each eye opening (`.eye-l` / `.eye-r` `clip-path` in the CSS) and move at most
7 px sideways, 3 px up and 4 px down in source pixels. Tune `RX`, `RY_UP`, `RY_DOWN`, `REACH`, `STIFF` and
`DAMP` at the top of the `Avatar` module. Tracking is mouse/pen only. Touch devices and
`prefers-reduced-motion` keep the neutral gaze; reduced motion also disables blinking.
If you replace the illustration, the eye positions must be measured again.
