import requests
import json

# get creds from file
with open('../creds.json') as f:
    creds = json.load(f)

url = "https://api.scorbit.io/api/machines/"

machines = []

while url:
    r = requests.get(url, auth=(creds["username"], creds["password"]))
    data = r.json()
    machines.extend(data['results'])
    url = data['next']

# save to file
with open('../data/machines.json', 'w') as f:
    json.dump(machines, f, indent=4)
