from typing import TypedDict, Optional


class CalendarEventStartStop(TypedDict):
    dateTime: Optional[str]
    date: Optional[str]
    timeZone: str

class CalendarEvent(TypedDict):
    id: str
    status: str
    created: str
    summary: str
    start: CalendarEventStartStop
    end: CalendarEventStartStop

class CalendarEventInsert(TypedDict):
    summary: str
    description: Optional[str]
    start: CalendarEventStartStop
    end: CalendarEventStartStop