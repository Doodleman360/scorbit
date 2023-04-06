# basic flask app
import json
import os.path
import requests
from flask import Flask, render_template

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


def get_scores(machines=(67444, 67443, 67445), testing=False):
    """
    Get scores from scorbit
    :param machines: List of machines to get scores from
    :param testing: If true, load scores from file
    :return: List of machines with their cores
    """
    scores = []

    for machine in machines:
        if testing:
            # check if file exists
            if not os.path.isfile(f"data/machine_{machine}.json") or not os.path.isfile(f"data/scores_{machine}.json"):
                print("File not found, Rerunning without testing")
                return get_scores()
            with open(f"data/machine_{machine}.json") as f:
                machineData = json.load(f)
            with open(f"data/scores_{machine}.json") as f:
                scoreData = json.load(f)
        else:
            # get data from scorbit
            machineUrl = f"https://api.scorbit.io/api/venuemachine/{machine}"
            scoreUrl = f"https://api.scorbit.io/api/venuemachine/{machine}/top_scores/"
            machineR = requests.get(machineUrl, auth=(creds["username"], creds["password"]))
            scoreR = requests.get(scoreUrl, auth=(creds["username"], creds["password"]))
            machineData = machineR.json()
            scoreData = scoreR.json()
            # save data
            with open(f"data/machine_{machine}.json", "w") as f:
                json.dump(machineData, f, indent=4)
            with open(f"data/scores_{machine}.json", "w") as f:
                json.dump(scoreData, f, indent=4)

        scores.append({"name": machineData['machine']['name'], "scores": []})
        for i in scoreData['all_time_venuemachine']:
            scores[-1]["scores"].append({"score": add_commas(i['score']), "initials": i['player']['initials']})
    return scores


@app.route('/')
def index():
    """
    This is the main page
    """
    return render_template('index.html', machines=get_scores(testing=True))


if __name__ == "__main__":
    app.run()
