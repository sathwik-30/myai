import json
import os

def load_knowledge():
    path=os.path.join(
        os.path.dirname(__file__),
        "data",
        "knowledge.json"
    )

    with open(path,"r",encoding="utf-8") as file:
        return json.load(file)