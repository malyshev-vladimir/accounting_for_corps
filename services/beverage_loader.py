import json
import os

def load_beverage_assortment():
    path = os.path.join("config", "beverages.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)