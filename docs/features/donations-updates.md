# Feature: donations-updates

> Quiet donate in About; one optional note after a version change; every cold-open GitHub installer check with changelog preview; Settings About Check for updates + Changelog.

## Acceptance criteria

- ✅ Quiet donate links in Settings → About only (not the header)
- ✅ First run records the installed version with no donate popup
- ✅ After a later launch where the installed version changed: one optional note (Donate | Not now)
- ✅ Every cold open, fetch latest GitHub release; compare installer filenames
- ✅ Newer matching asset and not dismissed: Download and install | Later, with changelog preview
- ✅ Settings → About: Check for updates + Changelog link next to version
- ✅ Failed fetch / timeout / placeholder repo: stay silent on launch; About shows status on manual check
- ✅ Prefs are device-local (`update_prefs.json`)
- ✅ No dark patterns

## Container map

| Layer | Device | Template stub |
|-------|--------|---------------|
| Logic | `src/trendalgo/device/about/` | `examples/web/src/about/` |
| View | `views/launch_prompt_dialog.py`, Settings About | `launchPrompt.ts` |
| Tests | `tests/test_device/test_product_update.py` | `productUpdate.test.ts` |
| Wiring | `app.py` ≤10 lines | `appBootstrap.ts` |
## Tests

- Automated: yes — `tests/test_device/test_product_update.py`

## Notes

- `release_repo` `OWNER/REPO` is a no-op
- Desktop asset prefix default: `TrendAlgo`
