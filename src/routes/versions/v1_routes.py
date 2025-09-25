from fastapi import APIRouter

from src.models.responses.generic import GenericResponse
from src.routes.webhooks import google_calendar

router = APIRouter()

router.include_router(google_calendar.router, prefix="/webhooks/google-calendar", tags=["Google Calendar"])

@router.get("/healthcheck")
async def healthcheck():
    return GenericResponse(data={"message": "Server is running normally!"})
