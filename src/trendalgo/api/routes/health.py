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
