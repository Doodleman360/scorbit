"""
Live-ish Scorbit Scoreboard
Author: Julien Sloan
Description: A scoreboard for scorbit.io
"""
from datetime import datetime, timedelta
import json
import os.path
import time
import requests
import random
from flask import Flask, redirect, render_template, request, send_from_directory
from flask_sock import Sock
from werkzeug.exceptions import HTTPException
from threading import Thread
from utils.utilFunctions import *

app = Flask(__name__, template_folder="templates")
app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 25}
sock = Sock(app)
client_list = []

# get creds from file
if os.path.isfile("creds.json"):
    with open('creds.json') as f:
        creds = json.load(f)
else:
    creds = {'username': input("Enter scorbit username: "), 'password': input("Enter scorbit password: "), 'venue id': input("Enter venue id: "), 'top x scores': int(input("Enter number of scores to display: ")), 'update frequency': int(input("Enter update frequency in seconds: ")), 'machine order': [], 'expire interval': int(input("Enter expire interval in days: "))}
    with open('creds.json', 'w') as f:
        print("Saving creds to file")
        print("If you want to set the machine order, edit creds.json and restart the program")
        json.dump(creds, f, indent=4)

topXScores = creds['top x scores']
updateFrequency = creds['update frequency']
venueID = creds['venue id']
expireInterval = creds['expire interval']


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
    today = datetime.today()

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

        if os.path.isfile(f"data/scores_local_{machine['venuemachine_id']}.json"):
            with open(f"data/scores_local_{machine['venuemachine_id']}.json") as f:
                localScoreData = json.load(f)
        else:
            localScoreData = []

        try:
            scores.append({"name": machineData['machine']['name'], "art": cache_backglass_art(machineData['machine']['backglass_art']), "scores": []})
            mostRecent = datetime(1970, 1, 1)
            mostRecentIndex = 0
            topExpiredScore = {"score": 0}
            for i in scoreData['all_time_venuemachine']:
                expireDate = today - timedelta(days=expireInterval)
                if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') < expireDate:
                    if i['score'] > topExpiredScore['score']:
                        topExpiredScore = {"score": i['score'], "initials": i['player']['initials'], "daysLeft": -(expireDate - datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')).days, "mostRecent": False, "updated": i['updated']}
                    continue
                scores[-1]["scores"].append({"score": add_commas(i['score']), "initials": i['player']['initials'], "mostRecent": False, "daysLeft": abs(expireDate - datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')).days, "updated": i['updated']})

            for i in localScoreData:
                expireDate = today - timedelta(days=expireInterval)
                if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') < expireDate:
                    if i['score'] > topExpiredScore['score']:
                        topExpiredScore = {"score": i['score'], "initials": i['player']['initials'], "daysLeft": -(expireDate - datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')).days, "mostRecent": False, "updated": i['updated']}
                    continue
                scores[-1]["scores"].append({"score": add_commas(i['score']), "initials": i['player']['initials'], "mostRecent": False, "daysLeft": abs(expireDate - datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')).days, "updated": i['updated']})

            for i in range(topXScores - len(scores[-1]["scores"])):
                scores[-1]["scores"].append({"score": "0", "initials": "N/A", "mostRecent": False, "daysLeft": 0, "updated": "1970-01-01T00:00:00.000Z"})
            # if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') > mostRecent:
            #     mostRecent = datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
            #     mostRecentIndex = count - 1
            # scores[-1]["scores"][mostRecentIndex]["mostRecent"] = True
            scores[-1]["scores"].sort(key=lambda x: int(x['score'].replace(",", "")), reverse=True)
            if topExpiredScore['score'] > 0 and int(scores[-1]["scores"][0]["score"].replace(",", "")) < topExpiredScore["score"]:
                scores[-1]["scores"].pop()
                topExpiredScore["score"] = add_commas(topExpiredScore["score"])
                scores[-1]["scores"].insert(0, topExpiredScore)
            count = 0
            for i in scores[-1]["scores"]:
                if datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ') > mostRecent:
                    mostRecent = datetime.strptime(i['updated'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    mostRecentIndex = count
                count += 1
            scores[-1]["scores"][mostRecentIndex]["mostRecent"] = True
        except Exception as e:
            # TODO: Add better error handling
            print(f"{type(e)} error on line {e.__traceback__.tb_lineno}: {e}")
            print("Error getting scores, using random scores")
            scores = get_random_scores()

    # try:
    #     scores.sort(key=lambda x: creds['machine order'].index(x['name']))
    # except Exception as e:
    #     print(f"unable to sort scores by physical location: {e}")
    #     pass
    return scores


def generate_scoreboard_data():
    """
    Generate scoreboard data
    :return:  json data
    """
    return json.dumps({'data': get_scores(cached=False), 'updateFrequency': updateFrequency, 'expireInterval': expireInterval})


@app.route('/')
def index():
    """
    This is the main page
    """
    return render_template('index.html', machineData=get_venue_data(), topXScores=topXScores, updateFrequency=updateFrequency, expireInterval=expireInterval)


@app.route('/data/art/<path:path>')
def art(path):
    """
    return art from data/art
    """
    return send_from_directory('data/art', path)


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
        else:
            # TODO: add input validation
            data = json.loads(data)
            print(data)
            if os.path.isfile(f"data/scores_local_{data['machine']}.json"):
                with open(f"data/scores_local_{data['machine']}.json") as f:
                    scores = json.load(f)
                    scores.append({"score": data["score"], "player": {"initials": data["initials"]}, "updated": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')})
            else:
                scores = [{"score": data["score"], "player": {"initials": data["initials"]}, "updated": datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')}]
            with open(f"data/scores_local_{data['machine']}.json", "w") as f:
                json.dump(scores, f)
            ws.send(generate_scoreboard_data())
    client_list.remove(ws)


@app.errorhandler(Exception)
def handle_exception(e):
    """
    Handle all exceptions
    :param e: exception
    :return: render error page
    """
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return render_template('error.html', error=e), e.code

    # now you're handling non-HTTP exceptions only
    print(f"{type(e)} error on line {e.__traceback__.tb_lineno}: {e}")
    print("Error, showing error page")
    return render_template('error.html', error=e), 500


if __name__ == "__main__":
    app.run()

app.send_update_loop_thread = Thread(target=send_update_loop, daemon=True)
app.send_update_loop_thread.start()
