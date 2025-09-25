from src.services.google_calendar import GoogleCalendarClient


class AppState:
    google_calendar_clients: list[GoogleCalendarClient] = []

app_state = AppState()