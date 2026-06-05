import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.api.deps import get_session
from app.services.portfolio import get_dashboard
from app.services.insights import generate_ai_insights
from app.db.models import AIInsight
from app.core.auth import get_current_user_id
from app.core.ratelimit import rate_limit_user

router = APIRouter()


@router.post(
    "/insights/refresh",
    dependencies=[Depends(rate_limit_user("rl_user_insights", "insights"))],
)
async def refresh_insights(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    portfolio_summary = await get_dashboard(session, user_id)
    insight = await generate_ai_insights(session, user_id, portfolio_summary)

    return {
        "id": str(insight.id),
        "insight_date": str(insight.insight_date),
        "model": insight.model,
        "observations": insight.observations,
    }


@router.get("/insights/latest")
async def latest_insights(
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    result = await session.execute(
        select(AIInsight)
        .where(AIInsight.user_id == user_id)
        .order_by(AIInsight.insight_date.desc())
        .limit(1)
    )
    insight = result.scalar_one_or_none()

    if not insight:
        return {"observations": []}

    return {
        "id": str(insight.id),
        "insight_date": str(insight.insight_date),
        "model": insight.model,
        "observations": insight.observations,
    }
