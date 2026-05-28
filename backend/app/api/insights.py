from fastapi import APIRouter, Depends
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.services.portfolio import get_dashboard
from app.services.insights import generate_ai_insights
from app.db.models import AIInsight

router = APIRouter()


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/insights/refresh")
async def refresh_insights(session=Depends(get_session)):
    portfolio_summary = await get_dashboard(session)
    insight = await generate_ai_insights(session, portfolio_summary)

    return {
        "id": str(insight.id),
        "insight_date": str(insight.insight_date),
        "model": insight.model,
        "observations": insight.observations,
    }


@router.get("/insights/latest")
async def latest_insights(session=Depends(get_session)):
    result = await session.execute(
        select(AIInsight).order_by(AIInsight.insight_date.desc()).limit(1)
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
