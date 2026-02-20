"""Agent orchestration endpoints."""

from fastapi import APIRouter, Depends, Query

from app.dependencies import AuthUser, get_current_user
from app.services.agent_orchestrator import orchestrator
from app.services.store import store

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/status")
async def get_agent_status(user: AuthUser = Depends(get_current_user)):
    """Get agent orchestrator status."""
    return orchestrator.get_status()


@router.post("/run")
async def run_agents(user: AuthUser = Depends(get_current_user)):
    """Manually trigger all agents to run now."""
    alerts = await orchestrator.run_all(user_id=user.id)
    return {
        "success": True,
        "alerts_generated": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "type": a.type.value,
                "severity": a.severity.value,
                "title": a.title,
                "symbol": a.asset_symbol,
                "confidence": a.confidence,
                "action": a.suggested_action.value,
            }
            for a in alerts
        ],
    }


@router.post("/scheduler/start")
async def start_scheduler(
    interval: int = Query(default=30, ge=5, le=360, description="Interval in minutes"),
    user: AuthUser = Depends(get_current_user),
):
    """Start the background agent scheduler."""
    orchestrator.start_scheduler(interval_minutes=interval)
    return {"success": True, "message": f"Scheduler started (every {interval} min)"}


@router.post("/scheduler/stop")
async def stop_scheduler(user: AuthUser = Depends(get_current_user)):
    """Stop the background agent scheduler."""
    orchestrator.stop_scheduler()
    return {"success": True, "message": "Scheduler stopped"}


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthUser = Depends(get_current_user),
):
    """Get persisted alert history from AI memory."""
    memories = store.get_memories(user.id, category="alert_history", limit=limit)
    alerts = []
    for m in memories:
        meta = m.get("metadata", {})
        alerts.append({
            "id": meta.get("alert_id", m.get("id")),
            "type": meta.get("type", "unknown"),
            "severity": meta.get("severity", "medium"),
            "title": m.get("content", ""),
            "description": meta.get("description", ""),
            "reasoning": meta.get("reasoning", ""),
            "symbol": meta.get("symbol"),
            "confidence": meta.get("confidence", 0.5),
            "suggested_action": meta.get("action", "monitor"),
            "created_at": m.get("created_at", ""),
        })
    return {"alerts": alerts, "total": len(alerts)}
