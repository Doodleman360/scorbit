# get json data from a url
import requests
import json

# get creds from file
with open('../creds.json') as f:
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


machines = [67444, 67443, 67445]

for machine in machines:
    machineUrl = f"https://api.scorbit.io/api/venuemachine/{machine}"
    scoreUrl = f"https://api.scorbit.io/api/venuemachine/{machine}/top_scores/"
    machineR = requests.get(machineUrl, auth=(creds["username"], creds["password"]))
    scoreR = requests.get(scoreUrl, auth=(creds["username"], creds["password"]))
    machineData = machineR.json()
    scoreData = scoreR.json()

    print(f"{machineData['machine']['name']} High Scores")
    for i in scoreData['all_time_venuemachine']:
        print(add_commas(i['score']), i['player']['initials'])
    print()
