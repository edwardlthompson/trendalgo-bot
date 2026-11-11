from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, str | bool]:
    state = request.app.state.trendalgo
    return {
        "status": "ok",
        "dry_run": state.bot.dry_run,
        "paused": state.risk_manager.state.paused,
    }


@router.get("/version")
def version() -> dict[str, str]:
    """Unauthenticated version probe (AUTH-01 exempt)."""
    return {"service": "trendalgo-api", "version": "0.1.0"}
