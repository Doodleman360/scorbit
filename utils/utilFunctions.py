"""
Utility functions for the app
Author: Julien Sloan
"""
import json
import os
import random

import requests


def random_initials():
    """
    Generate random initials
    """
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))


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


def cache_backglass_art(link):
    """
    Cache backglass art
    :param link: link to backglass art
    :return: path to cached backglass art
    """
    if os.path.isfile(f"data/art/{link.split('/')[-1]}"):
        return f"data/art/{link.split('/')[-1]}"
    else:
        r = requests.get(link)
        if r.status_code == 200:
            with open(f"data/art/{link.split('/')[-1]}", "wb") as f:
                f.write(r.content)
            return f"data/art/{link.split('/')[-1]}"
        else:
            print(f"Error downloading {link}")
            return None