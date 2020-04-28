import requests
from bs4 import BeautifulSoup
import unicodedata

with requests.Session() as s:

    payload = {
        "tbAnvandarnamn": "nils.forssén",
        "tbLosenord": "N1sseP1sse02!",
        "btnLoggaIn": "Logga in"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.122 Safari/537.36"

    }

    page = s.get("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", headers = headers)
    soup = BeautifulSoup(page.content, features="lxml")
    payload["__VIEWSTATE"] = soup.select_one("#__VIEWSTATE")["value"]
    payload["__VIEWSTATEGENERATOR"] = soup.select_one("#__VIEWSTATEGENERATOR")["value"]

    payload["__VIEWSTATE"] = soup.find("input", attrs={"name" : "__VIEWSTATE"})["value"]
    payload["__VIEWSTATEGENERATOR"] = soup.find("input", attrs={"name" : "__VIEWSTATEGENERATOR"})["value"]
    payload["__EVENTVALIDATION"] = soup.find("input", attrs={"name" : "__EVENTVALIDATION"})["value"]

    r = s.post("https://fogis.svenskfotboll.se/Fogisdomarklient/login/Login.aspx", data=payload, headers=headers)
    open_page = s.get("https://fogis.svenskfotboll.se/Fogisdomarklient/Uppdrag/UppdragUppdragLista.aspx")

    # Parse the HTML schedule-table into a list with dictionaries for every coming game 
    soup = BeautifulSoup(open_page.content, features="lxml")
    data = []
    gameHeaders = ["Time", "Competition", "Round", "Number", "Game", "Location", "Referees", ]
    table = soup.find('table', attrs={'class':'fogisInfoTable'})
    tableBody = table.find('tbody')

    rows = tableBody.find_all('tr')
    for row in rows:
        game = dict(zip(gameHeaders, [unicodedata.normalize("NFKC", item.text.strip().replace("  ","")).replace("\n", "").replace("\r", "") for item in row.find_all('td')]))
        
        data.append(game)

    data.pop(0)
