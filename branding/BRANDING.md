# Branding kit

Replaceable product identity for **TrendAlgo Bot**, adopted from
[agent-project-bootstrap](https://github.com/edwardlthompson/agent-project-bootstrap) v0.17.0.

## Single sources of truth

| Concern | Edit here | Then run |
|---------|-----------|----------|
| Colors, type, spacing | [`design-tokens/design-tokens.json`](../design-tokens/design-tokens.json) | `python3 scripts/sync-design-tokens.py` |
| Logos / favicon / heroes | [`assets/`](assets/) | `python3 scripts/sync-design-tokens.py` |
| Name, pitch, README copy | [`product.json`](product.json) | `python3 scripts/generate-project-readme.py` |
| Voice guidelines | [`voice.md`](voice.md) | (docs only) |

Official color stylesheet (generated): [`official-colors.css`](official-colors.css).

## Asset inventory

| File | Use |
|------|-----|
| `assets/logo-mark.svg` | App mark; synced to web `icon.svg` / `logo.svg` |
| `assets/logo-mark-mono.svg` | Monochrome / print |
| `assets/logo-wordmark.svg` | Wordmark only |
| `assets/logo-lockup.svg` | Mark + wordmark |
| `assets/favicon.svg` | Browser tab |
| `assets/app-icon-512.svg` | Export to store `icon.png` 512×512 (`[HUMAN]`) |
| `assets/readme-hero.svg` | README banner |
| `assets/social-preview.svg` | GitHub / OG 1280×640 (upload PNG export in repo Settings → Social preview) |

## Clear space & contrast

- Keep at least 1/8 of the mark’s width as padding around the mark.
- Prefer mark-on-dark (`#1a1a2e`) or mono mark on light surfaces.
- Check contrast for primary on surface in both light and dark themes after token edits.

## Rebrand checklist

1. Update `meta.name` and colors in `design-tokens/design-tokens.json`.
2. Replace SVGs under `branding/assets/` (keep filenames).
3. Fill `branding/product.json` (keep `"mode": "template"` unless you intend to replace the live README).
4. Run `python3 scripts/sync-design-tokens.py`.
5. Run `python3 scripts/generate-project-readme.py`.
6. Align UI strings (`locales`), `manifest.webmanifest`, and GitHub About.
7. Export PNGs for social preview when ready — do not commit large binaries unless intentional.

## Template vs product README

- `"mode": "template"` (**TrendAlgo default**) — generator writes only `generated/README.preview.md`. Root `README.md` stays the hand-authored self-hosted setup guide.
- `"mode": "product"` — generator **overwrites** root `README.md` with the short pitch README. Do not enable this unless a human has approved replacing the setup guide.

Pitch preview: [`generated/README.preview.md`](generated/README.preview.md).

## Android note

The Android module is pruned in this repo. `sync-design-tokens.py` skips Android drawable sync when `examples/android/` is absent.
