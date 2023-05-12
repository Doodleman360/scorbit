# basic flask app
from datetime import datetime, timedelta
import json
import os.path
import time
import requests
import random
from flask import Flask, redirect, render_template, request
from flask_sock import Sock
from werkzeug.exceptions import HTTPException
from threading import Thread

app = Flask(__name__, template_folder="templates")
app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 25}
sock = Sock(app)
client_list = []

# TODO: pin grand champ

# get creds from file
with open('creds.json') as f:
    creds = json.load(f)

topXScores = creds['top x scores']
updateFrequency = creds['update frequency']
venueID = creds['venue id']


def send_update():
    """
    Send update to all clients
    """
    data = generate_scoreboard_data()
    clients = client_list.copy()
    for client in clients:
        try:
            client.send(data)
        except Exception as e:
            print(e)
            print("Closing connection to client")
            client_list.remove(client)
    print(f"Sent update to {len(client_list)} clients")


def send_update_loop():
    """
    Send update to all clients every updateFrequency seconds
    """
    while True:
        time.sleep(updateFrequency)
        send_update()


# function to add commas to numbers
def add_commas(n):
    """
    Add commas to numbers
    :param n: Number to add commas to
    :return: String with commas
    """
    n = str(n)
    if len(n) <= 3:
        return n
    return add_commas(n[:-3]) + ',' + n[-3:]


def get_venue_data():
    """
    Get venue data from file or scorbit
    :return: Venue data
    """
    if os.path.isfile(f"data/venue_{venueID}.json"):
        with open(f"data/venue_{venueID}.json") as f:
            venueData = json.load(f)
    else:
        venueUrl = f'https://api.scorbit.io/api/venue/{venueID}/venuemachines/'
        venueR = requests.get(venueUrl, auth=(creds["username"], creds["password"]))
        venueData = venueR.json()
        with open(f"data/venue_{venueID}.json", "w") as f:
            json.dump(venueData, f, indent=4)

    # sort scores by physical location
    try:
        venueData['results'].sort(key=lambda x: creds['machine order'].index(x['machine_name']))
    except Exception as e:
        print(f"unable to sort scores by physical location: {e}")
        pass
    return venueData


# noinspection SpellCheckingInspection
def get_scores(cached=False):
    """
    Get scores from scorbit
    :param cached: If true, load scores from file
    :return: List of machines with their cores
    """
    scores = []
    venueData = get_venue_data()

    for machine in venueData['results']:
        if cached:
            # check if file exists
            if not os.path.isfile(f"data/machine_{machine['venuemachine_id']}.json") or not os.path.isfile(f"data/scores_{machine['venuemachine_id']}.json"):
                print("File not found, Rerunning without cache")
                return get_scores(cached=False)
            with open(f"data/machine_{machine['venuemachine_id']}.json") as f:
                machineData = json.load(f)
            with open(f"data/scores_{machine['venuemachine_id']}.json") as f:
                scoreData = json.load(f)
        else:
            # get data from scorbit
            machineUrl = f"https://api.scorbit.io/api/venuemachine/{machine['venuemachine_id']}"
            scoreUrl = f"https://api.scorbit.io/api/venuemachine/{machine['venuemachine_id']}/top_scores/"
            machineR = requests.get(machineUrl, auth=(creds["username"], creds["password"]))
            scoreR = requests.get(scoreUrl, auth=(creds["username"], creds["password"]))
            machineData = machineR.json()
            scoreData = scoreR.json()
            # save data
            with open(f"data/machine_{machine['venuemachine_id']}.json", "w") as f:
                json.dump(machineData, f, indent=4)
            with open(f"data/scores_{machine['venuemachine_id']}.json", "w") as f:
                json.dump(scoreData, f, indent=4)
        try:
            scores.append({"name": machineData['machine']['name'], "art": machineData['machine']['backglass_art'], "scores": []})
            count = 1
            mostRecent = datetime(1970, 1, 1)
            mostRecentIndex = 0
            for i in scoreData['all_time_venuemachine']:
                if count == topXScores + 1:
                    break
                # check if score was in the last month
                today = datetime.today()
                expireDate = today - timedelta(days=60)
                if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') < expireDate:
                    continue
                if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') > mostRecent:
                    mostRecent = datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    mostRecentIndex = count - 1
                scores[-1]["scores"].append({"rank": count, "score": add_commas(i['score']), "initials": i['player']['initials'], "mostRecent": False, "daysLeft": abs(expireDate - datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')).days})
                count += 1
            for i in range(topXScores - len(scores[-1]["scores"])):
                scores[-1]["scores"].append({"rank": count, "score": "N/A", "initials": "N/A"})
                count += 1
            scores[-1]["scores"][mostRecentIndex]["mostRecent"] = True
        except Exception as e:
            # TODO: Add better error handling
            print(e)
            print("Error getting scores, using random scores")
            scores = get_random_scores()


    # try:
    #     scores.sort(key=lambda x: creds['machine order'].index(x['name']))
    # except Exception as e:
    #     print(f"unable to sort scores by physical location: {e}")
    #     pass
    return scores


def get_random_scores():
    """
    Get generate random scores for testing
    """
    scores = []
    for i in range(random.randint(2, 5)):
        choice = get_random_pinball()
        scores.append({"name": choice[0], "art": choice[1], "scores": []})
        for j in range(10):
            scores[-1]["scores"].append({"rank": j + 1, "score": add_commas(random.randint(1000000, 100000000)), "initials": random_initials()})
    return scores


def random_initials():
    """
    Generate random initials
    """
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))


def get_random_pinball():
    """
    Get random pinball name and art
    """
    with open("data/machines.json") as f:
        data = json.load(f)
    choice = random.choice(data)
    while not choice["backglass_art"]:
        choice = random.choice(data)
    return choice["name"], choice["backglass_art"]


def generate_scoreboard_data():
    """
    Generate scoreboard data
    :return:  json data
    """
    return json.dumps({'data': get_scores(cached=False), 'updateFrequency': updateFrequency})


@app.route('/')
def index():
    """
    This is the main page
    """
    return render_template('index.html', machineData=get_venue_data(), topXScores=topXScores, updateFrequency=updateFrequency)


@sock.route("/sock")
def connect(ws):
    """
    Connect to websocket
    :param ws: websocket object
    """
    client_list.append(ws)
    print("Client connected")
    ws.send(generate_scoreboard_data())
    while True:
        data = ws.receive()
        if data == "close":
            break
    client_list.remove(ws)


@app.errorhandler(Exception)
def handle_exception(e):
    """
    Handle all exceptions
    :param e: exception
    :return: redirect to http.cat
    """
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return render_template('error.html', error=e), e.code

    # now you're handling non-HTTP exceptions only
    print(e)
    return render_template('error.html', error=e), 500


if __name__ == "__main__":
    app.run()

app.send_update_loop_thread = Thread(target=send_update_loop, daemon=True)
app.send_update_loop_thread.start()
