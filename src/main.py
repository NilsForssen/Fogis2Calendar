import requests
from bs4 import BeautifulSoup
import unicodedata
import googleCalendar
import datetime
import sys
import os
import pkg_resources.py2_warn

"""
Python Script for adding fogis events to Google Calendar

credenials.json from Google API project is to be located in working directory.

A token.pickle file will be created in Working Directory.
Deleting this file will result in you having to approve
access to Google Calendar.

Script can be executed:
-> Manually by running executable(.py) and using GUI
-> Automatically by CMD passing fogis credentials as arguments
e.g script.exe(.py) myUser myPass

The latter can  be used with Windows task scheduler to schedule calendar updates.

Author: Nils Forssén, Jämtland County, Sweden
"""


def getDataPage(uName, pWord):
    """
    Login to fogis and return the datapage.
    If not accessible, return None.
    """

    with requests.Session() as session:

        # Data to post to loginPage
        payload = {
            "tbAnvandarnamn": uName,
            "tbLosenord": pWord,
            "btnLoggaIn": "Logga in"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36"
        }

        # Log in page
        loginPage = session.get("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", headers=headers)

        # post with all required information
        soup = BeautifulSoup(loginPage.content, features="lxml")

        payload["__VIEWSTATE"] = soup.select_one("#__VIEWSTATE")["value"]
        payload["__VIEWSTATEGENERATOR"] = soup.select_one("#__VIEWSTATEGENERATOR")["value"]
        payload["__VIEWSTATE"] = soup.find("input", attrs={"name" : "__VIEWSTATE"})["value"]
        payload["__VIEWSTATEGENERATOR"] = soup.find("input", attrs={"name" : "__VIEWSTATEGENERATOR"})["value"]
        payload["__EVENTVALIDATION"] = soup.find("input", attrs={"name" : "__EVENTVALIDATION"})["value"]

        # Post with the login credentials and additional required information
        session.post("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", data=payload, headers=headers)

        # Schedule is located here
        dataPage = session.get("https://fogis.svenskfotboll.se/Fogisdomarklient/Uppdrag/UppdragUppdragLista.aspx")

        if b"FOGIS - Domarinloggning" in dataPage.content:

            # Login unsuccessfull, access to dataPage url was not granted.
            # e.g. username or password incorrect, account locked/banned etc.

            return None
        else:

            # Login successfull

            return dataPage


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
      "description": "{0}\n{1}\nMatchnummer: {2}".format(game["game"], game["referees"], game["number"]),
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


def updateCalendar(page):
    """
    Update the calendar with games from given dataPage
    """

    # Parse the HTML schedule-table into a list with dictionaries for every coming game 
    soup = BeautifulSoup(page.content, features="lxml")

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

        googleCalendar.createEvent(game)
        
        print("Event created! {0}".format(game["start"]["dateTime"]))


if __name__ == "__main__":

    if len(sys.argv) < 2:

        # No arguments passed, launch GUI prompt for username and password

        import tkinter as tk

        root = tk.Tk()

        # Make the Entrys expand to fill empty space
        root.grid_columnconfigure(1, weight=1)

        # Window icon
        root.iconbitmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "calendar_icon.ico"))
        root.title("Fogis2Calendar")

        # GUI elements
        header = tk.Label(text="Enter your fogis credentials", font='Helvetica 16')
        uNameLabel = tk.Label(text="Username:", font="Helvetica 10")
        uNameEntry = tk.Entry()
        pWordLabel = tk.Label(text="Password:", font="Helvetica 10")
        pWordEntry = tk.Entry()

        promptString = tk.StringVar()
        promptString.set("")
        promptLabel = tk.Label(textvariable=promptString, font="Helvetica 10")

        def btnUpdateCalendar():
            """
            Comprehensive update calendar function linked to btn in GUI 
            """

            page = getDataPage(uNameEntry.get(), pWordEntry.get())

            if page is not None:

                promptString.set("Updated!")
                promptLabel.config(fg="green2")
                updateCalendar(page)

                # "Updated"

            else:

                promptString.set("Login unsuccessfull!")
                promptLabel.config(fg="red2")


        btn = tk.Button(text="Update Calendar", font="Helvetica 10 bold", command=btnUpdateCalendar, bg="green2", activebackground="green2")

        # Grid GUI elements
        header.grid(columnspan=2, row=0, column=0, sticky="NSEW")
        uNameLabel.grid(row=1, sticky="W")
        uNameEntry.grid(row=1, column=1, sticky="EW")
        pWordLabel.grid(row=2, sticky="W")
        pWordEntry.grid(row=2, column=1, sticky="EW")
        promptLabel.grid(columnspan=2, row=3, sticky="NSEW")
        btn.grid(columnspan=2, row=4)

        root.mainloop()

    else:

        # username and password arguments passed, don't launch GUI

        try:
            username = sys.argv[1]
            password = sys.argv[2]
        except IndexError:
            print("Both username and password must be passed as arguments")
            sys.exit()

        page = getDataPage(username, password)

        if page is not None:
            updateCalendar(page)
        else:
            print("Login unsuccessfull")