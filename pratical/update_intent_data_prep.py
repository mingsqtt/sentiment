import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import re
import pickle
from lmpylib.nlp import md5, search_all_datetimes
from addr_loc_from_to_augment import gen_company_addr, gen_company, gen_addr, gen_company_abbr
from addr_loc_from_to_augment import block_street_regex1, unit_building_regex


with open("data/bodies.pickle", "rb") as f:
    bodies = pickle.load(f)

ss = set()
for b, body_id in enumerate(bodies):
    first_doc = bodies[body_id][0]
    if first_doc["sender"].find("haulio") == -1:
        replaced_lines = first_doc["replaced_lines"]
        for line in replaced_lines:
            line_lower = line.lower()
            if (line_lower.find("update") > 0) or (line_lower.find("change") > 0) or (line_lower.find("postpone") > 0) or (line_lower.find("delay") > 0) or (line_lower.find("instead") > 0) or (line_lower.find("revise") > 0) or (line_lower.find("now is") > 0) or (line_lower.find("the new") > 0) or (line_lower.find("the latest") > 0) or (line_lower.find("is now") > 0) or (line_lower.find("become") > 0):
                if line_lower.find("charge") == -1:
                    if not ss.__contains__(line):
                        ss.add(line)

pd.DataFrame({
    "update": "",
    "update_later": "",
    "line": list(ss)
}).to_csv("data/update_intent_data.csv", index=False)