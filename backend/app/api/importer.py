"""CSV import router — F4.

POST /import/csv?dry_run=true   → validate + preview; no DB writes (authenticated)
POST /import/csv?dry_run=false  → execute import              (authenticated)
GET  /import/csv/template       → download CSV template       (public, IP rate-limited)

Routing split rationale: the template is a hardcoded static file with no user data.
Browser-native <a href> download cannot send Authorization headers, so the template
must be publicly accessible. Import endpoints remain fully gated behind JWT auth.
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response

from app.api.deps import get_session
from app.core.auth import get_current_user_id
from app.core.ratelimit import rate_limit_ip, rate_limit_user
from app.services.importer import (
    CSV_TEMPLATE,
    parse_and_validate,
    execute_import,
)

# Public router — no auth dependency. Registered in main.py without _per_user.
# Template is static content; IP rate limiting prevents trivial abuse.
public_router = APIRouter(prefix="/import", tags=["import"])

# Authenticated router — registered in main.py with _per_user.
router = APIRouter(prefix="/import", tags=["import"])


@public_router.get(
    "/csv/template",
    dependencies=[Depends(rate_limit_ip("rl_market_default"))],
)
async def download_template():
    """Return a downloadable CSV template with example rows. Public — no auth required."""
    return Response(
        content=CSV_TEMPLATE,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="wealthsignal_import_template.csv"'},
    )


@router.post(
    "/csv",
    dependencies=[Depends(rate_limit_user("rl_user_import", "import"))],
)
async def import_csv(
    dry_run: bool = Query(default=True, description="true=preview only, false=execute import"),
    file: UploadFile = File(...),
    session=Depends(get_session),
    user_id: uuid.UUID = Depends(get_current_user_id),
):
    """Parse, validate, and optionally execute a CSV transaction import.

    On dry_run=true: returns preview rows + any validation errors; no writes.
    On dry_run=false: executes the import for valid rows only; returns summary.
    If any row-level errors exist on dry_run=false, the import is still executed
    for valid rows. The caller must inspect the errors list to identify skipped rows.
    """
    if file.content_type not in ("text/csv", "application/csv", "application/vnd.ms-excel", "application/octet-stream"):
        # Be permissive on content-type; actual content is validated in parse_and_validate.
        pass

    content = await file.read()

    try:
        valid_rows, errors = parse_and_validate(content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if dry_run:
        return {
            "dry_run": True,
            "valid_count": len(valid_rows),
            "error_count": len(errors),
            "preview": [r.to_preview() for r in valid_rows],
            "errors": errors,
        }

    if not valid_rows:
        raise HTTPException(status_code=400, detail="No valid rows to import after validation")

    summary = await execute_import(session, user_id, valid_rows)
    return {
        "dry_run": False,
        "errors": errors,
        "error_count": len(errors),
        **summary,
    }
