import os
import queue
import threading
import time
from datetime import datetime
from threading import Thread
from typing import Callable

from src.services.google_calendar import GoogleCalendarClient


class CalendarPollingManager:
    def __init__(self, google_calendar_client: GoogleCalendarClient, poll_interval = 60):
        self.calendar_client = google_calendar_client
        self.poll_interval = poll_interval
        self.polling_thread: Thread | None = None
        self.stop_event = threading.Event()
        self.event_queue = queue.Queue()
        self.event_callbacks: list[Callable] = []
        self.handled_event_ids: list[str] = []
        self.sync_token_path = "sync_token.txt"

        self.last_sync_token = self._read_sync_token()

    def add_event_handler(self, callback_func: Callable):
        self.event_callbacks.append(callback_func)

    def start_polling(self):
        if self.polling_thread and self.polling_thread.is_alive():
            print("Polling already running!")
            return

        self.stop_event.clear()
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        print(f"Started calendar polling service (interval {self.poll_interval}s)")

    def stop_polling(self):
        if self.polling_thread:
            self.stop_event.set()
            self.polling_thread.join(timeout=5)
            print("Stopped calendar polling service")

    def get_events(self, timeout = 1):
        try:
            return self.event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _polling_loop(self):
        while not self.stop_event.is_set():
            try:
                events = [event for event in self._poll_for_changes() if event["id"] not in self.handled_event_ids]
                if events and len(events) > 0:
                    self.handled_event_ids += [event["id"] for event in events]
                    event_data = {
                        "timestamp": datetime.now(),
                        "events": events,
                        "calendar_client": self.calendar_client
                    }
                    self.event_queue.put(event_data)

                    for callback in self.event_callbacks:
                        try:
                            callback(event_data)
                        except Exception as e:
                            print(f"Callback error: {e}")

            except Exception as e:
                print(f"Polling error: {e}")

            self.stop_event.wait(timeout=self.poll_interval)


    def _poll_for_changes(self):
        try:
            if self.last_sync_token:
                response = self.calendar_client.fetch_events(
                    sync_token=self.last_sync_token
                )

                while response["nextPageToken"] is not None and response["syncToken"] is None:
                    response = self.calendar_client.fetch_events(time_min=time.time(), next_page_token=response["nextPageToken"])

                if response["syncToken"] is not None:
                    self._save_sync_token(response["syncToken"])

                return response["items"]
            else:
                # Initial events won't be handled
                print("Scrolling through pages until sync token is returned....")
                response = self.calendar_client.fetch_events(time_min=time.time())
                while response["nextPageToken"] is not None and response["syncToken"] is None:
                    response = self.calendar_client.fetch_events(time_min=time.time(), next_page_token=response["nextPageToken"])

                if response["syncToken"] is not None:
                    self._save_sync_token(response["syncToken"])

                return []
        except Exception as e:
            print(f"Error polling calendar: {e}")

    def _read_sync_token(self):
        try:
            with open(self.sync_token_path, "r") as file:
                content = file.read().strip()
            return content if content else None
        except FileNotFoundError:
            return None

    def _save_sync_token(self, sync_token: str):
        os.makedirs(os.path.dirname(self.sync_token_path), exist_ok=True)

        with open(self.sync_token_path, "w") as file:
            file.write(sync_token)
            self.last_sync_token = sync_token
