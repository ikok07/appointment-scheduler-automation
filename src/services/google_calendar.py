import datetime
import json
import os
import threading
import time
import uuid
from threading import Thread

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build, Resource


class GoogleCalendarClient:
    is_auth = False

    watch_channel_id: str | None= None
    watch_channel_resource_id: str | None = None
    watch_channel_expiration: int | None = None
    watch_channel_renew_thread: Thread | None = None

    def __init__(self, calendar_id: str):
        self.scopes = ["https://www.googleapis.com/auth/calendar"]
        self.credentials = Credentials.from_service_account_info(
            json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")),
            scopes=self.scopes
        )
        self.calendar_service = build("calendar", "v3", credentials=self.credentials)
        self.calendar_id = calendar_id
        if self.credentials:
            self.is_auth = True

    def watch_calendar(self):
        if not self.is_auth:
            raise Exception("Calendar authentication is not setup!")

        if self.watch_channel_id:
            return

        self.watch_channel_id = str(uuid.uuid4())
        self.watch_channel_expiration = int(time.time() * 1000 + int(os.getenv("GOOGLE_CALENDAR_WATCH_CHANNEL_EXPIRATION")))

        try:
            response = self.calendar_service.events().watch(
                calendarId=self.calendar_id,
                body={
                    "id": self.watch_channel_id,
                    "type": "web_hook",
                    "address": os.getenv("GOOGLE_CALENDAR_EVENT_CREATED_WEBHOOK_URL"),
                    "token": os.getenv("GOOGLE_CALENDAR_EVENT_CREATED_WEBHOOK_TOKEN"),
                    "expiration": self.watch_channel_expiration
                }
            ).execute()
            print(f"Calendar ID: {self.calendar_id} started watch channel with id: {self.watch_channel_id}!")
            self.watch_channel_resource_id = response["resourceId"]

            # Schedule auto-renew timer
            self._schedule_renewal()
        except Exception as e:
            print("Failed to create Google Calendar Watch Channel!")
            raise e

    def close_watch_channel(self):
        if self.watch_channel_renew_thread and self.watch_channel_renew_thread.is_alive():
            self.watch_channel_renew_thread.cancel()
            self.watch_channel_renew_thread = None
        try:
            response = self.calendar_service.channels().stop(
                body={
                    "id": self.watch_channel_id,
                    "resourceId": self.watch_channel_resource_id
                }
            ).execute()
            print(f"Stopped watch channel {self.watch_channel_id} for calendar {self.calendar_id}")
            self.watch_channel_id = None
            self.watch_channel_resource_id = None
        except Exception as e:
            print(f"Failed to stop Google Calendar Watch Channel with id: {self.watch_channel_id}")
            raise e

    def renew_watch_channel(self):
        self.close_watch_channel()
        self.watch_calendar()

    def fetch_events(self, time_min: float | None = None, time_max: float | None = None, sync_token: str | None = None):
        if not self.calendar_service:
            raise Exception("No calendar service available!")

        try:
            response = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=datetime.datetime.fromtimestamp(time_min).isoformat() + "Z" if time_min else None,
                timeMax=datetime.datetime.fromtimestamp(time_max).isoformat() + "Z" if time_max else None,
                singleEvents=True,
                syncToken=sync_token
            ).execute()

            return {
                "items": response["items"] if "items" in response else [],
                "syncToken": response["nextSyncToken"] if "nextSyncToken" in response else None
            }
        except Exception as e:
            print("Failed to fetch google calendar events!")
            print(e)
            raise e

    def _schedule_renewal(self):
        now_ms = int(time.time() * 1000)
        ttl_ms = self.watch_channel_expiration - now_ms

        renew_in = max(60 * 1000, int(ttl_ms * 0.9)) # either 90% of TTL or 60s

        print(f"Scheduling renewal in {renew_in/1000:.1f} seconds")

        self.watch_channel_renew_thread = threading.Timer(renew_in / 1000, self.renew_watch_channel)
        self.watch_channel_renew_thread.start()