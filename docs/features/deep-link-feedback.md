# Feature: deep-link Settings → About → Feedback

## Intent

`trendalgo://settings/about/feedback` opens Settings and the Feedback dialog (device).

## Acceptance criteria

- ✅ Deep links into Feedback carry a sanitized subject when provided
- ✅ Invalid payloads fall back (no crash; unknown routes ignored)

## Smoke scenario

1. Given a Feedback deep link in argv
2. When the device app starts
3. Then Feedback is shown without crashing

## Container map

| Layer | Device |
|-------|--------|
| Logic | `src/trendalgo/device/deep_link.py` |
| View | `views/feedback_dialog.py` |
| Tests | `tests/test_device/test_deep_link.py` |
| Wiring | `app.py` `_offer_startup_extras` |
## Tests

- Automated: yes — `tests/test_device/test_deep_link.py`

## Fallback validation

- Command: `python3 scripts/agent-run.py watch-agent-gates --once --autofix --scope auto`
