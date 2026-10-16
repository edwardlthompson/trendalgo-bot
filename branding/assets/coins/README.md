# Coin icons (device Scanner)

Put official coin logo files here (`BTC.png`, `ETH.png`, …), or use one of the search paths below.

## Resolution order

1. `TRENDALGO_COIN_ICONS` environment variable (directory of icons)
2. `branding/assets/coins/from-retired-web-backup/` (local junction; **do not commit**)
3. `branding/assets/coins/` (curated files you choose to commit)
4. `examples/web/public/icons/coins/` (retired tree; may be absent)

## Local junction (recommended for PWA look)

If you still have the 2026-10-10 PWA backup:

```powershell
New-Item -ItemType Junction -Path "branding\assets\coins\from-retired-web-backup" `
  -Target "C:\Users\edwar\trendalgo-retired-pwa-2026-10-10\examples\web\public\icons\coins"
```

Or set:

```powershell
$env:TRENDALGO_COIN_ICONS = "C:\Users\edwar\trendalgo-retired-pwa-2026-10-10\examples\web\public\icons\coins"
```

Do **not** `git add` the full icon dump (~977 files). Repo hygiene keeps that out of history.

Recover from git history if needed: `git checkout origin/main -- examples/web/public/icons/coins` then copy a curated set into this folder before committing.
