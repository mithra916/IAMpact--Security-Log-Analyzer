from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import json

from app.parsing.parser import parse_cloudtrail_event
from app.detection.risk_engine import calculate_risk
from app.ai.explain import generate_explanation

router = APIRouter()


class LogRequest(BaseModel):
    logs: Any


@router.post("/api/analyze-logs")
async def analyze_logs(payload: LogRequest):
    try:
        logs = payload.logs

        if isinstance(logs, str):
            logs = json.loads(logs)

        if isinstance(logs, dict):
            logs = [logs]

        if not isinstance(logs, list):
            raise HTTPException(
                status_code=400,
                detail="Logs must be a JSON object or array"
            )

        alerts = []

        for log in logs:
            parsed = parse_cloudtrail_event(log)
            scored = calculate_risk(parsed)
            explanation = generate_explanation(scored)

            alerts.append({
                **scored,
                "explanation": explanation
            })

        alerts = sorted(
            alerts,
            key=lambda x: x.get("risk_score", 0),
            reverse=True
        )

        return {
            "total_logs": len(logs),
            "total_alerts": len(alerts),
            "top_alert": alerts[0] if alerts else None,
            "alerts": alerts
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )