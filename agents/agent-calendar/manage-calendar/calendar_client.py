import requests
from icalendar import Calendar
import datetime
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

class CalendarClient:
    def __init__(self, ical_url):
        self.ical_url = ical_url

    def fetch_events(self, days_ahead=7):
        """Récupère les événements pour les X prochains jours."""
        try:
            response = requests.get(self.ical_url)
            response.raise_for_status()
            
            calendar = Calendar.from_ical(response.content)
            
            now = datetime.datetime.now(pytz.utc)
            end_period = now + datetime.timedelta(days=days_ahead)
            
            events = []
            for component in calendar.walk():
                if component.name == "VEVENT":
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    
                    # Convert to UTC if needed
                    if isinstance(start, datetime.datetime):
                        if start.tzinfo is None:
                            start = pytz.utc.localize(start)
                        else:
                            start = start.astimezone(pytz.utc)
                    else:
                        # It's a date object
                        start = datetime.datetime.combine(start, datetime.time.min).replace(tzinfo=pytz.utc)
                        
                    if isinstance(end, datetime.datetime):
                        if end.tzinfo is None:
                            end = pytz.utc.localize(end)
                        else:
                            end = end.astimezone(pytz.utc)
                    else:
                        end = datetime.datetime.combine(end, datetime.time.max).replace(tzinfo=pytz.utc)

                    if now <= start <= end_period or (start <= now <= end):
                        events.append({
                            "summary": str(component.get('summary')),
                            "start": start.isoformat(),
                            "end": end.isoformat(),
                            "location": str(component.get('location', 'N/A')),
                            "description": str(component.get('description', ''))
                        })
            
            # Sort events by start date
            events.sort(key=lambda x: x['start'])
            return events
            
        except Exception as e:
            print(f"Error fetching calendar: {e}")
            return []

if __name__ == "__main__":
    # Test
    URL = os.getenv("TUM_ICAL_URL")
    if URL:
        client = CalendarClient(URL)
        events = client.fetch_events(3)
        for e in events:
            print(f"{e['start']} - {e['summary']} @ {e['location']}")
    else:
        print("TUM_ICAL_URL not found in .env")
