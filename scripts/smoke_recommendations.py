"""Smoke-test recently added product-recommendation features against a live API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
results: list[tuple[str, bool, str]] = []


def req(method: str, path: str, body: dict | None = None, headers: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    request = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw[:300]}
        return exc.code, payload
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": str(exc)}


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(("PASS" if ok else "FAIL"), name, detail[:180])


def main() -> int:
    st, health = req("GET", "/health")
    check("health", st == 200, str(health)[:80])

    st, dash = req("GET", "/dashboard")
    check(
        "dashboard",
        st == 200 and "dry_run" in dash,
        f"dry_run={dash.get('dry_run')} paused={dash.get('risk', {}).get('paused')}",
    )

    st, _ = req("POST", "/risk/pause")
    check("risk.pause", st == 200, str(st))
    st, dash2 = req("GET", "/dashboard")
    check("risk.paused_flag", bool(dash2.get("risk", {}).get("paused")), str(dash2.get("risk"))[:120])
    st, _ = req("POST", "/risk/resume")
    check("risk.resume", st == 200, str(st))

    st, snap = req("GET", "/scanner/snapshot")
    check(
        "scanner.snapshot",
        st == 200,
        f"degraded={snap.get('degraded')} as_of={snap.get('as_of')} ops={len(snap.get('opportunities') or [])}",
    )
    st, run = req("POST", "/scanner/run")
    check(
        "scanner.run",
        st == 200 and ("opportunities" in run or "degraded" in run),
        f"degraded={run.get('degraded')} ops={len(run.get('opportunities') or [])}",
    )
    st, settings = req("GET", "/scanner/settings")
    check("scanner.settings", st == 200 and "interval_minutes" in settings, str(settings)[:100])

    st, ai = req("GET", "/ai/recommendations")
    check("ai.recommendations", st == 200 and "recommendations" in ai, f"n={len(ai.get('recommendations') or [])}")
    st, curated = req("GET", "/ai/curated-library")
    check("ai.curated", st == 200 and "presets" in curated, f"n={len(curated.get('presets') or [])}")
    st, ref = req("GET", "/growth/referral")
    check("growth.referral", st == 200 and "code" in ref, str(ref)[:80])
    st, lb = req("GET", "/growth/leaderboard")
    check("growth.leaderboard", st == 200 and "rows" in lb, f"n={len(lb.get('rows') or [])}")

    st, wf = req("POST", "/research/walk-forward", {})
    check("research.walk_forward", st in (200, 422), f"status={st}")
    st, hm = req("GET", "/research/hyperopt-heatmap")
    check("research.heatmap", st == 200, f"keys={list(hm)[:8] if isinstance(hm, dict) else hm}")

    st, job = req("POST", "/hyperopt", {"strategy": "multi-tf-example", "pair": "BTC/USD", "epochs": 10})
    job_id = job.get("job_id") or job.get("id")
    check("hyperopt.create", st in (200, 201) and bool(job_id or job.get("status")), str(job)[:140])
    if job_id:
        time.sleep(0.5)
        st, j2 = req("GET", f"/hyperopt/{job_id}")
        check(
            "hyperopt.status",
            st == 200 and str(j2.get("status")) in {"queued", "running", "failed", "done", "complete"},
            str(j2)[:140],
        )
    else:
        check("hyperopt.status", False, "no job_id")

    st, tg = req("POST", "/webhooks/telegram", {"message": {"text": "/status", "chat": {"id": 1}}})
    # 503 = ingress not configured (expected without TELEGRAM_* env); still proves route exists
    check("telegram.webhook", st in (200, 401, 403, 422, 503), f"status={st} body={str(tg)[:100]}")

    st, tv = req("POST", "/webhooks/tradingview", {"ticker": "BTCUSD", "action": "buy"})
    check("tradingview.webhook", st in (200, 401, 403, 422), f"status={st} body={str(tv)[:120]}")

    st, arb = req("GET", "/portfolio/arbitrage")
    if st == 404:
        st, arb = req("GET", "/portfolio-advanced/arbitrage")
    check("arbitrage", st == 200, f"status={st} keys={list(arb)[:8] if isinstance(arb, dict) else arb}")

    st, bill = req("GET", "/billing/dashboard")
    check("billing.dashboard", st == 200, f"keys={list(bill)[:8] if isinstance(bill, dict) else bill}")
    st, ln = req("POST", "/billing/lightning-invoice", {"period": "current", "amount_usd": 1})
    check("billing.lightning", st == 501, f"status={st} body={str(ln)[:120]}")
    st, pg = req("GET", "/platform/postgres/status")
    check("platform.postgres", st == 200, f"body={str(pg)[:140]}")

    st, ov = req("GET", "/portfolio/overview")
    dates = []
    if isinstance(ov, dict):
        dates = ov.get("snapshot_dates") or []
    if dates:
        st, hist = req("GET", f"/portfolio/history/{dates[0]}")
        check("portfolio.history", st == 200, f"date={dates[0]} keys={list(hist)[:8] if isinstance(hist, dict) else hist}")
    else:
        st, hist = req("GET", "/portfolio/history/1970-01-01")
        check(
            "portfolio.history",
            st in (200, 404),
            f"no snapshot_dates; status={st} body={str(hist)[:100]}",
        )

    st, params = req("GET", "/strategies")
    check("strategies", st == 200, f"status={st}")

    st, inbox = req("GET", "/notifications/inbox")
    check("notifications.inbox", st == 200, f"status={st}")

    # Vite proxy / PWA shell
    try:
        with urllib.request.urlopen("http://127.0.0.1:5173/", timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        check("vite.shell", resp.status == 200 and ("app" in html.lower() or "root" in html.lower() or "<!doctype" in html.lower()), f"len={len(html)}")
    except Exception as exc:  # noqa: BLE001
        check("vite.shell", False, str(exc))

    try:
        with urllib.request.urlopen("http://127.0.0.1:5173/api/v1/health", timeout=15) as resp:
            proxied = json.loads(resp.read().decode())
        check("vite.api_proxy", resp.status == 200, str(proxied)[:80])
    except Exception as exc:  # noqa: BLE001
        check("vite.api_proxy", False, str(exc))

    passed = sum(1 for _, ok, _ in results if ok)
    failed = [(n, d) for n, ok, d in results if not ok]
    print("---")
    print(f"SUMMARY {passed}/{len(results)} passed")
    for name, detail in failed:
        print("FAILED", name, detail)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
