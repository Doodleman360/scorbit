# basic flask app
import json

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


def get_scores(machines=(67444, 67443, 67445)):
    """
    Get scores from scorbit
    :return: List of machines with their cores
    """
    scores = []

    for machine in machines:
        machineUrl = f"https://api.scorbit.io/api/venuemachine/{machine}"
        scoreUrl = f"https://api.scorbit.io/api/venuemachine/{machine}/top_scores/"
        machineR = requests.get(machineUrl, auth=(creds["username"], creds["password"]))
        scoreR = requests.get(scoreUrl, auth=(creds["username"], creds["password"]))
        machineData = machineR.json()
        scoreData = scoreR.json()

        scores.append({"name": machineData['machine']['name'], "scores": []})
        for i in scoreData['all_time_venuemachine']:
            scores[-1]["scores"].append({"score": add_commas(i['score']), "initials": i['player']['initials']})
    return scores


@app.route('/')
def index():
    """
    This is the main page
    """
    return render_template('index.html', machines=get_scores())


if __name__ == "__main__":
    app.run()
