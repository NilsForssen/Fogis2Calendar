import requests
from bs4 import BeautifulSoup
import unicodedata
import googleCalendar
import datetime
import argparse

# Take fogis username and password as arguments, this is personal data
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Create game events in google calendar from schedule from fogis")

parser.add_argument("username", action="store", help="fogis username")
parser.add_argument("password", action="store", help="fogis password")
args = parser.parse_args()


with requests.Session() as session:

    payload = {
        "tbAnvandarnamn": args.username,
        "tbLosenord": args.password,
        "btnLoggaIn": "Logga in"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36"
    }

    # Log in page
    logInPage = session.get("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", headers = headers)

    # post with all required information
    soup = BeautifulSoup(logInPage.content, features="lxml")
    payload["__VIEWSTATE"] = soup.select_one("#__VIEWSTATE")["value"]
    payload["__VIEWSTATEGENERATOR"] = soup.select_one("#__VIEWSTATEGENERATOR")["value"]

    payload["__VIEWSTATE"] = soup.find("input", attrs={"name" : "__VIEWSTATE"})["value"]
    payload["__VIEWSTATEGENERATOR"] = soup.find("input", attrs={"name" : "__VIEWSTATEGENERATOR"})["value"]
    payload["__EVENTVALIDATION"] = soup.find("input", attrs={"name" : "__EVENTVALIDATION"})["value"]

    session.post("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", data=payload, headers=headers)

    # Schedule is located here
    dataPage = session.get("https://fogis.svenskfotboll.se/Fogisdomarklient/Uppdrag/UppdragUppdragLista.aspx")

    # Parse the HTML schedule-table into a list with dictionaries for every coming game 
    soup = BeautifulSoup(dataPage.content, features="lxml")

    data = []
    gameHeaders = ["time", "competition", "round", "number", "game", "location", "referees", ]

    table = soup.find('table', attrs={'class':'fogisInfoTable'})
    tableBody = table.find('tbody')

    rows = tableBody.find_all('tr')
    for row in rows:

        # Remove some indesirable characters and whitespace from each cell
        game = dict(zip(gameHeaders, [unicodedata.normalize("NFKC", item.text.strip().replace("  ","")).replace("\n", "").replace("\r", "") for item in row.find_all('td')]))
        
        data.append(game)

    # Remove empty top row
    data.pop(0)

    # Create google calendar event for each game in fogis table
    for game in data:

        event = {}

        # If time is TBD, set event time to 00:00:00
        if ":" in game["time"][-5:]:
            startTime =  datetime.datetime.strptime(game["time"][-5:], "%H:%M")
            duration = datetime.datetime.strptime("01:30", "%H:%M")
        else:
            startTime = datetime.datetime.strptime("00:00", "%H:%M")
            duration = datetime.datetime.strptime("00:00", "%H:%M")

        endTime = startTime + datetime.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
        
        # create google calendar friendly event dictionary
        event = {
          "summary": "Domare {0}".format(game["competition"]),
          "location": "{0}".format(game["location"].replace("GoogleBingHitta.se", "")),
          "description": "{0}".format(game["referees"]),
          "start": {
            "dateTime": "{0}T{1}+02:00".format(game["time"][:10], startTime.strftime("%H:%M:%S"))
          },
          "end": {
            "dateTime": "{0}T{1}+02:00".format(game["time"][:10], endTime.strftime("%H:%M:%S"))
          },

          "reminders": {
            "useDefault": True
          },
        }

        # Create event
        googleCalendar.createEvent(event)

        print("event created at {0}".format(startTime))

