from fastapi import APIRouter

router = APIRouter()


@router.get("/pairs")
def list_pairs() -> dict[str, list[str]]:
    return {"pairs": ["BTC/USD", "ETH/USD"]}
