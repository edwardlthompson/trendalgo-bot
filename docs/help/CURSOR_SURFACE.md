# Cursor surface (MCP + skills) — your steps

Agent already prepared the repo. You only need a **Cursor restart** (and a token only if MCP github is red).

## Do this (about 1 minute)

1. **Reload Cursor**  
   Press `Ctrl+Shift+P` → type **Reload Window** → Enter  
   (or quit and reopen Cursor)

2. **Confirm MCP**  
   Open Cursor Settings → **MCP** (or Tools)  
   You should see **github** and **depsonar** without red errors.

   If they stay red on Windows: Node is often installed but **not on PATH**. Re-run  
   `python scripts/agent-run.py activate-cursor-surface -- --force-mcp`  
   (rewrites `npx` → `C:\Program Files\nodejs\npx.cmd`), then Reload again.

3. **Only if github MCP is red / missing token**  
   In PowerShell:

   ```powershell
   gh auth login
   [Environment]::SetEnvironmentVariable("GITHUB_TOKEN", (gh auth token), "User")
   ```

   Then do step 1 again (Reload Window).

## Optional re-check (agent already ran this)

```powershell
python scripts/agent-run.py activate-cursor-surface
```

## Do not

- Commit `.cursor/mcp.json` or any token
- Change the FOSS MCP allowlist for personal SaaS tools

## Related

- [`docs/MCP_RECIPES.md`](../MCP_RECIPES.md)
- [`docs/SKILLS_RECIPES.md`](../SKILLS_RECIPES.md)
