# Third-Party Licenses

> Generated and maintained per release. See pre-release gate in `docs/INITIALIZATION_PROMPT.md` Section 7a.

## Project License

This project is licensed under the Elastic License 2.0 (source-available). See [`LICENSE`](LICENSE) and [`docs/LICENSE_MODEL.md`](docs/LICENSE_MODEL.md).

## Dependencies

Run license audits for active stacks:

```bash
# Python (pip)
cd examples/python && uv run pip-licenses --format=markdown

# Rust / Go (optional stacks — MIT stubs; expand when deps are added)
grep 'license' examples/rust/Cargo.toml
head -1 examples/go/go.mod
```

`[AUTO]` CI runs `scripts/check-license-compliance.sh` on each push.

## Attribution

When bundling dependencies in releases (desktop binary, MSI, etc.), include
this file or a generated `NOTICE` file in the distribution artifact.

## Incompatible Licenses

`[HUMAN]` must approve any dependency with copyleft licenses (GPL, AGPL) that
may affect distribution. Document exceptions in `DECISION_LOG.md`.
