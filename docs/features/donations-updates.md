# Feature: donations-updates

> Quiet donate in About; one optional note after a version change; silent daily GitHub installer check.

## Acceptance criteria

- ✅ Quiet donate links in Settings → About only (not the header)
- ✅ First run records the installed version with no donate popup
- ✅ After a later launch where the installed version changed: one optional note (Donate | Not now)
- ✅ Once per 24 hours, fetch latest GitHub release; compare installer filenames
- ✅ Newer matching asset and not dismissed: Install | Later
- ✅ Failed fetch / timeout / placeholder repo: stay silent
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
