import json
from datetime import date
from google import genai
from app.core.config import settings
from app.db.models import AIInsight


def generate_rule_based_observations(portfolio_summary: dict) -> dict:
    observations = []

    total_pnl = portfolio_summary.get("total_pnl", 0)
    pnl_percent = portfolio_summary.get("pnl_percent", 0)

    if total_pnl > 0:
        observations.append({
            "category": "performance",
            "severity": "info",
            "title": "Portfolio is in profit",
            "message": f"Your portfolio is up by {pnl_percent:.2f}% overall."
        })
    elif total_pnl < 0:
        observations.append({
            "category": "performance",
            "severity": "medium",
            "title": "Portfolio is in loss",
            "message": f"Your portfolio is down by {abs(pnl_percent):.2f}% overall."
        })
    else:
        observations.append({
            "category": "performance",
            "severity": "info",
            "title": "No profit or loss yet",
            "message": "Your current portfolio value is equal to your invested amount."
        })

    return {"observations": observations}


async def generate_gemini_observations(portfolio_summary: dict) -> dict:
    if not settings.gemini_api_key:
        return generate_rule_based_observations(portfolio_summary)

    prompt = f"""
You are a portfolio observability analyst.

You are not a financial advisor.
Do not recommend buying, selling, or holding assets.
Do not predict guaranteed returns.

Analyze this portfolio summary JSON and return JSON only.

Return this exact shape:
{{
  "observations": [
    {{
      "category": "performance | allocation | liquidity | risk | trend",
      "severity": "info | medium | high",
      "title": "short title",
      "message": "concise observation"
    }}
  ]
}}

Portfolio summary:
{json.dumps(portfolio_summary)}
"""

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
    except Exception:
        # Gemini unavailable or auth failure — fall back to deterministic rules
        return generate_rule_based_observations(portfolio_summary)

    try:
        text = response.text.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        return json.loads(text)
    except Exception:
        return {
            "observations": [
                {
                    "category": "ai",
                    "severity": "medium",
                    "title": "AI response could not be parsed",
                    "message": "Gemini returned a response, but it was not valid JSON."
                }
            ],
            "raw": response.text,
        }


async def generate_ai_insights(session, portfolio_summary: dict) -> AIInsight:
    if settings.ai_provider == "gemini":
        observations = await generate_gemini_observations(portfolio_summary)
    else:
        observations = generate_rule_based_observations(portfolio_summary)

    insight = AIInsight(
        insight_date=date.today(),
        observations=observations,
        model=settings.gemini_model if settings.ai_provider == "gemini" else "rules",
    )

    session.add(insight)
    await session.commit()
    await session.refresh(insight)

    return insight
