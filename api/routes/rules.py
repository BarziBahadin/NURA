from fastapi import APIRouter, Depends
from core.auth import verify_api_key
from core.orchestrator import _rules_engine

router = APIRouter()


@router.get("/rules")
async def list_rules(_: None = Depends(verify_api_key)):
    if _rules_engine is None:
        return {"rules": [], "total": 0}
    rules = [
        {
            "title": r["title"],
            "keyword_count": len(r["keyword_roots"]),
            "keywords": sorted(r["keyword_roots"])[:20],
            "response_preview": r["response"][:300],
        }
        for r in _rules_engine._rules
    ]
    return {"rules": rules, "total": len(rules)}
