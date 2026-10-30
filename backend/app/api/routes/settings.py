from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SystemConfiguration
from app.schemas.configuration import ConfigurationRead, ConfigurationUpdate
from app.services.configuration import DEFAULT_CONFIGURATION, load_configuration


router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

def _read_configuration(configuration: SystemConfiguration | None) -> ConfigurationRead:
    if configuration is None:
        return ConfigurationRead(
            **DEFAULT_CONFIGURATION,
            updated_at=datetime.now(timezone.utc),
        )
    return ConfigurationRead.model_validate(configuration, from_attributes=True)


@router.get("", response_model=ConfigurationRead)
def get_configuration(session: Session = Depends(get_db)) -> ConfigurationRead:
    return _read_configuration(session.get(SystemConfiguration, 1))


@router.patch("", response_model=ConfigurationRead)
def update_configuration(
    payload: ConfigurationUpdate,
    session: Session = Depends(get_db),
) -> ConfigurationRead:
    configuration = session.get(SystemConfiguration, 1)
    if configuration is None:
        configuration = load_configuration(session)
        session.add(configuration)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(configuration, key, value)
    configuration.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(configuration)
    return _read_configuration(configuration)
