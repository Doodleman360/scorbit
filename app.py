# basic flask app
import json
import os.path
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# get creds from file
with open('creds.json') as f:
    creds = json.load(f)


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


def get_scores(venueID=17029, testing=False):
    """
    Get scores from scorbit
    :param venueID: ID of venue to get scores from
    :param testing: If true, load scores from file
    :return: List of machines with their cores
    """
    scores = []
    venueUrl = f'https://api.scorbit.io/api/venue/{venueID}/venuemachines/'
    venueR = requests.get(venueUrl, auth=(creds["username"], creds["password"]))
    venueData = venueR.json()

    for machine in venueData['results']:
        if testing:
            # check if file exists
            if not os.path.isfile(f"data/machine_{machine['venuemachine_id']}.json") or not os.path.isfile(f"data/scores_{machine['venuemachine_id']}.json"):
                print("File not found, Rerunning without testing")
                return get_scores(venueID=venueID, testing=False)
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

        scores.append({"name": machineData['machine']['name'], "art": machineData['machine']['backglass_art'], "scores": []})
        count = 1
        for i in scoreData['all_time_venuemachine']:
            if count == 11:
                break
            scores[-1]["scores"].append({"rank": count, "score": add_commas(i['score']), "initials": i['player']['initials']})
            count += 1
        for i in range(10 - len(scores[-1]["scores"])):
            scores[-1]["scores"].append({"rank": count, "score": "N/A", "initials": "N/A"})
            count += 1
    return scores


@app.route('/<venueID>')
@app.route('/')
def index(venueID=17029):
    """
    This is the main page
    """
    return render_template('index.html', machines=get_scores(venueID=venueID, testing=True))


if __name__ == "__main__":
    app.run()
