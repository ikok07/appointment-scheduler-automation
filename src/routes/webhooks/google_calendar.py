import os

from fastapi import APIRouter
from starlette import status
from starlette.requests import Request

from src.models.errors.api import APIError
from src.models.responses.generic import GenericResponse

router = APIRouter()

# @router.post("/event-created")
# async def event_created(request: Request):
#     headers = request.headers
#
#     # Extract Google-specific headers
#     channel_id = headers.get('X-Goog-Channel-Id')
#     resource_state = headers.get('X-Goog-Resource-State')
#     resource_id = headers.get('X-Goog-Resource-Id')
#     resource_uri = headers.get('X-Goog-Resource-Uri')
#     message_number = headers.get('X-Goog-Message-Number')
#
#     # Verify the token if you set one
#     token = headers.get('X-Goog-Channel-Token')
#     if token != os.getenv("GOOGLE_CALENDAR_EVENT_CREATED_WEBHOOK_TOKEN"):
#         print("Invalid token received")
#         raise APIError(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized")
#
#     print(f"Webhook received - Channel: {channel_id}, State: {resource_state}")
#
#     if resource_state == "sync":
#         print(f"Watch channel for resource id: {resource_id} is working correctly!")
#     elif resource_state == "exists":
#         pass
#
#     return '', 200