from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import get_marcopolo_service, require_marcopolo_access
from ..models import DataConnectionOperationResponse, DataConnectionOperationsResponse
from ..services.auth import UserSession
from ..services.marcopolo import MarcoPoloService, MarcoPoloServiceError

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/examples", response_model=DataConnectionOperationsResponse)
async def list_data_connection_operations(
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> DataConnectionOperationsResponse:
    return marcopolo.data_connection_operations()


@router.post("/run", response_model=DataConnectionOperationResponse)
async def invoke_data_connection_operation(
    request: Request,
    user_session: UserSession = Depends(require_marcopolo_access),
    marcopolo: MarcoPoloService = Depends(get_marcopolo_service),
) -> DataConnectionOperationResponse:
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="JSON object body is required.")

    example_id = payload.get("exampleId") or payload.get("example_id")
    if not example_id:
        raise HTTPException(status_code=422, detail="exampleId is required.")

    try:
        return await marcopolo.invoke_data_connection_operation(user_session, example_id)
    except MarcoPoloServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
