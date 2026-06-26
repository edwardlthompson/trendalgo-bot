from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/debug/logs")
def debug_logs(request: Request, limit: int = 100) -> dict[str, list[str]]:
    state = request.app.state.trendalgo
    logs = list(state.debug_logs)[: max(1, min(limit, 500))]
    return {"logs": logs}
