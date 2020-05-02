from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def getCredentials():
    """
    Get the current credentials from the pickle file, 
    If not available, create new file with credentials
    """

    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return creds


service = build('calendar', 'v3', credentials=getCredentials())

def createEvent(event):
    """
    Create google calendar event using the standard event formatting 
    """

    event = service.events().insert(calendarId="primary", body=event).execute()

    return event


def deleteEvent(eventId):
    """
    Delete event with given id from google calendar
    """

    service.events().delete(calendarId="primary", eventId=eventId).execute()


def listEvents(**kwargs):
    """
    Return list of all google calendar events
    """

    events = service.events().list(calendarId="primary", **kwargs).execute()

    return events
