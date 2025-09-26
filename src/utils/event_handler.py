import math
import os
from datetime import datetime, timezone, timedelta

import pytz

from src.models.calendar_event import CalendarEvent, CalendarEventInsert, CalendarEventStartStop
from src.services.google_calendar import GoogleCalendarClient

def check_overlap(d1_start: float, d1_end: float, d2_start: float, d2_end: float):
    return d1_start < d2_end and d2_start < d1_end

def new_event_handler(event_data: dict):
    calendar_client: GoogleCalendarClient = event_data["calendar_client"]
    new_events: list[CalendarEvent] = [CalendarEvent(**event) for event in event_data["events"] if "Ден 1" in event["summary"]]

    if len(new_events) > 0:
        print(f"AUTOMATIZATION STARTED FOR CALENDAR ID: {calendar_client.calendar_id}")

    calendar_client.unify_event_start_stop_dates(new_events)

    for event in new_events:
        event_start = datetime.fromisoformat(event["start"]["dateTime"]) if event["start"]["dateTime"] else datetime.fromisoformat(event["start"]["date"])
        event_end = datetime.fromisoformat(event["end"]["dateTime"]) if event["end"]["dateTime"] else datetime.fromisoformat(event["end"]["date"])

        # Convert to timestamps
        event_start = event_start.timestamp()
        event_end = event_end.timestamp()
        event_duration_seconds = event_end - event_start

        # Define start and end period
        start_period_days_offset = 0

        start_period = ((datetime
                        .fromtimestamp(event_start, tz=pytz.timezone(os.getenv("GOOGLE_CALENDAR_TIMEZONE")))
                        .replace(hour=int(os.getenv("BOOKING_START_HOUR")), minute=0) + timedelta(days=start_period_days_offset))
                        .timestamp())
        end_period = ((datetime
                      .fromtimestamp(start_period, tz=pytz.timezone(os.getenv("GOOGLE_CALENDAR_TIMEZONE")))
                      .replace(hour=int(os.getenv("BOOKING_END_HOUR")), minute=0) + timedelta(days=2))
                      .timestamp())

        # Fetch all events for period
        events_in_period = calendar_client.fetch_events(
            time_min=start_period,
            time_max=end_period
        )["items"]
        events_in_period = [event_in_period for event_in_period in events_in_period if calendar_client.check_busy(event_in_period)]

        calendar_client.unify_event_start_stop_dates(events_in_period)

        # Set the next dates for booking
        appointment_percentages = [float(percentage) for percentage in os.getenv("APPOINTMENT_PERCENTAGES").split(',')]
        next_dates: list[dict] = []
        first_date_target_events = [event_in_period for event_in_period in events_in_period if datetime.fromisoformat(event_in_period["start"]["dateTime"]).date() == datetime.fromtimestamp(event_start).date() and "Ден 1" in event_in_period["summary"]]
        previous_max_events_for_date = len(first_date_target_events)

        for i in range(2):
            next_date_start = (datetime.fromtimestamp(start_period) + timedelta(days=i + 1)).timestamp()
            next_date_end = (datetime.fromtimestamp(next_date_start) + timedelta(seconds=event_duration_seconds)).timestamp()

            max_events_for_date = math.ceil(appointment_percentages[i] * previous_max_events_for_date)
            print(appointment_percentages[i], previous_max_events_for_date, max_events_for_date)
            previous_max_events_for_date = max_events_for_date

            events_for_date = [event for event in events_in_period if datetime.fromisoformat(event["start"]["dateTime"]).date() == datetime.fromtimestamp(next_date_start).date()]

            target_event_for_date = [event for event in events_in_period if f"Ден {i + 2}" in event["summary"]]

            # If max events reached - break
            if len(target_event_for_date) >= max_events_for_date:
                break

            # Find available time slot
            original_next_date_start = next_date_start
            next_date_not_suitable = False

            for index, event_for_date in enumerate(events_for_date):
                start = datetime.fromisoformat(event_for_date["start"]["dateTime"]).timestamp()
                end = datetime.fromisoformat(event_for_date["end"]["dateTime"]).timestamp()
                overlaps = check_overlap(
                    next_date_start,
                    next_date_end,
                    start,
                    end
                )

                if overlaps:
                    next_date_start = end
                    next_date_end = (datetime.fromtimestamp(next_date_start) + timedelta(seconds=event_duration_seconds)).timestamp()
                    # Check if the next date gets out of the max booking time for the day
                    if datetime.fromtimestamp(next_date_end) > datetime.fromtimestamp(original_next_date_start).replace(hour=int(os.getenv("BOOKING_END_HOUR"))):
                        next_date_not_suitable = True
                        break

            if not next_date_not_suitable:
                next_dates.append({"start": next_date_start, "end": next_date_end})

        # Book next dates
        for index, next_date in enumerate(next_dates):
            calendar_client.book_event(CalendarEventInsert(
                summary=f"Ден {index + 2}",
                start=CalendarEventStartStop(
                    dateTime=datetime.fromtimestamp(next_date["start"], tz=pytz.timezone(os.getenv("GOOGLE_CALENDAR_TIMEZONE"))).isoformat(),
                    date=None,
                    timeZone=os.getenv("GOOGLE_CALENDAR_TIMEZONE")
                ),
                end=CalendarEventStartStop(
                    dateTime=datetime.fromtimestamp(next_date["end"], tz=pytz.timezone(os.getenv("GOOGLE_CALENDAR_TIMEZONE"))).isoformat(),
                    date=None,
                    timeZone=os.getenv("GOOGLE_CALENDAR_TIMEZONE")
                )
            ))