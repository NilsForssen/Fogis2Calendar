import requests
from bs4 import BeautifulSoup
import unicodedata
import googleCalendar
import datetime
import sys



try:
    username = sys.argv[1]
    password = sys.argv[2]
except IndexError:
    print("Both username and password must be passed as arguments")
    sys.exit()



with requests.Session() as session:

    payload = {
        "tbAnvandarnamn": username,
        "tbLosenord": password,
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


    def formatGame(game):
        """
        Turn given game into google calendar event format
        """

        # If time is TBD, set event time to 00:00:00
        if ":" in game["time"][-5:]:
            startTime =  datetime.datetime.strptime(game["time"][-5:], "%H:%M")
            duration = datetime.datetime.strptime("01:30", "%H:%M")
        else:
            startTime = datetime.datetime.strptime("00:00", "%H:%M")
            duration = datetime.datetime.strptime("00:00", "%H:%M")

        endTime = startTime + datetime.timedelta(hours=duration.hour, minutes=duration.minute, seconds=duration.second)
        
        # create google-calendar-friendly event out of given game
        gameEvent = {
          "summary": "Domare {0}".format(game["competition"]),
          "location": "{0}".format(game["location"].replace("GoogleBingHitta.se", "")),
          "description": "{0}\nMatchnummer: {1}".format(game["referees"], game["number"]),
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

        return gameEvent


    # Format all games from fogis
    data = list(map(formatGame, data))
    comingEvents = [event for event in googleCalendar.listEvents(timeMin=data[0]["start"]["dateTime"], timeMax=data[-1]["end"]["dateTime"])["items"]]


    # Delete all coming games to refresh them
    for comingEvent in comingEvents:
        
        try:
            lastLine = comingEvent["description"].splitlines()[-1]

            if "Matchnummer: " in lastLine:

                # The event is a previously uploaded game, delete it
                # All currently active games will be added later
                # This game could have e.g. been canceled recently, thus it needs removal

                googleCalendar.deleteEvent(comingEvent["id"])

        except KeyError:

            # An event wiithout a description was found, this is not a game from fogis

            pass


    for game in data:

        # Add all new events, in case the event was just deleted, this will just refresh it
        print("Event created at {0}".format(game["start"]["dateTime"]))
        googleCalendar.createEvent(game)