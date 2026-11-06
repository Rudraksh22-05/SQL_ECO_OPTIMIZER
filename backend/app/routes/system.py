from fastapi import APIRouter, HTTPException
import psutil

from app.services.os_monitor import collect_system_health

router = APIRouter(tags=["system diagnostics"])


@router.get("/system/health")
def system_health():
    """Return current host resource metrics for the System Diagnostics view."""
    try:
        return collect_system_health()
    except (psutil.Error, OSError, RuntimeError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"System metrics are temporarily unavailable: {error.__class__.__name__}",
        ) from error
