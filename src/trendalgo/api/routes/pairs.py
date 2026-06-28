from fastapi import APIRouter

from trendalgo.exchanges.pairs import list_pairs_for_exchange

router = APIRouter()


@router.get("/pairs")
def list_pairs() -> dict[str, list[str]]:
    return {"pairs": list_pairs_for_exchange("kraken")}
