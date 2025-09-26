import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app_state import app_state
from src.services.calendar_polling_manager import CalendarPollingManager
from src.services.google_calendar import GoogleCalendarClient
from src.utils.event_handler import new_event_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        for calendar_id in os.getenv("GOOGLE_CALENDAR_IDS").split(','):
            client = GoogleCalendarClient(calendar_id=calendar_id)
            poller = CalendarPollingManager(
                google_calendar_client=client,
                poll_interval=5
            )
            poller.add_event_handler(new_event_handler)
            poller.start_polling()
            app_state.google_calendar_clients.append(
                client
            )
        yield
    except Exception as e:
        print("Failed to start server!")
        print(e)
