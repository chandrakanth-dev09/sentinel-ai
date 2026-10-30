from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.rca.engine import analyze_incident
from app.schemas.rca import RCARequest, RCAResponse


router = APIRouter(prefix="/api/v1/incidents", tags=["root cause analysis"])


@router.post("/analyze", response_model=RCAResponse)
def analyze(
    payload: RCARequest,
    session: Session = Depends(get_db),
) -> RCAResponse:
    try:
        return analyze_incident(session, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
