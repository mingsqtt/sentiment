import numpy as np
import pandas as pd
from datetime import datetime
import re
import pickle

from lmpylib.core import *
from lmpylib import nlp

from nltk import word_tokenize


raw_email_data = pd.read_csv("data/email_20200731.csv")
raw_email_data["time"] = [datetime.fromtimestamp(ts) for ts in raw_email_data["ts_utc"]]
raw_email_data["time"] = pd.to_datetime(raw_email_data["time"])


email_regex = "(?i)(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"
container_no_regex = "(?<![0-9a-zA-Z_])[A-Z]{4}[\s-]?[0-9]{3}[\s-]?[0-9]{1}[\s-]?[0-9]{2}[\s-]?[0-9]{1}(?![0-9a-zA-Z_])"
job_code_regex = "(?:IM|EX|OWI|OWE|OWO|OW)-[0-9]{3}-[0-9]{4}"
money_regex = "(?i)(?:SGD|USD|S\$|US\$|\$)\s*\d+(?:,\d{3})*(?:\.[0-9]{1,2})?"
postal_regex = "(?i)(?:^|(?<=[\s,:<>]))((?:Singapore|SG|S)\s*[\(\-]?[0-9]{6}\)?)(?![0-9a-zA-Z\-/_])"
mailto_regex = "<mailto:[\w\d%_+\.\?;@\-]+(?:\s|>|$)"
url_regex = "<?(?:https://|http://|www\.)[^\s]+(?:\s|$)"
tel_regex = "\(?\+\s?\(?65\)?\s*\d{4}[\s\-]?\d{4}"
num_code_regex = "[^\s:=,;!?<>\(\)'\"]*\d{5,}[^\s:=,;!?<>\(\)'\"]*"
complex_code_regex = "(?:[^\s:=,;!?<>\(\)'\"]+\d{3,}[^\s:=,;!?<>\(\)'\"]*)|(?:[^\s:=,;!?<>\(\)'\"]*\d{3,}[^\s:=,;!?<>\(\)'\"]+)"


vessel_part_spec = "([A-Za-z\-@]+(?: [A-Za-z\-@]+)*)"
vessel_part_gen = "([\w\-@]+(?: [\w\-@]+)*)"
vsl_lbl_part = "(?:barge name|barge to|barge|vessel name|vessel to|vessel|vsl name|vsl to|vsl)\s*:?\s*"
labelled_vessel_part_spec = vsl_lbl_part + vessel_part_spec
labelled_vessel_part_gen = vsl_lbl_part + vessel_part_gen
voyage_part = "((?:\d[\w\-]{1,5})|(?:[\w\-]{0,5}\d[\w\-]{0,5})|(?:[\w\-]{1,5}\d))"
voy_lbl_part = "(?:v\.|v\s|voyage no.|voyage no|voyage number|voyage|voy. no.|voy. no|voy. number|voy.|voy no.|voy no|voy number|voy)\s*:?\s*"
labelled_voyage_part = voy_lbl_part + voyage_part
vessel_voyage_regex1 = "(?i)" + labelled_vessel_part_gen + "[,\.]?\s*" + labelled_voyage_part + "(?:[,\.\s]|$)"
vessel_voyage_regex2 = "(?i)" + labelled_vessel_part_spec + "[,\.\s]" + voyage_part + "(?:[,\.\s]|$)"
vslvoy_comb_lbl_part = "(?:(?:barge|vessel name|vessel|vsl name|vsl)\s?[/,]\s?(?:v\.|v\s|voyage no.|voyage no|voyage number|voyage|voy. no.|voy. no|voy. number|voy.|voy no.|voy no|voy number|voy))\s*:?\s*"
vessel_voyage_regex3 = "(?i)" + vslvoy_comb_lbl_part + vessel_part_gen + "\s*[/,]\s*" + "(?:" + voy_lbl_part + ")?" + voyage_part + "(?:[,\.\s]|$)"
vessel_voyage_regex4 = "(?i)" + vslvoy_comb_lbl_part + vessel_part_spec + "\s+" + "(?:" + voy_lbl_part + ")?" + voyage_part + "(?:[,\.\s]|$)"
vessel_only_regex = "(?i)" + labelled_vessel_part_gen + "(?:[,\.\n]|$)"
voyage_only_regex = "(?i)" + labelled_voyage_part + "(?:[,\.\s]|$)"

def extract_vessel_voyage(text):
    match = re.search(vessel_voyage_regex1, text)
    if match is not None:
        return match[1], match[2]
    else:
        match = re.search(vessel_voyage_regex2, text)
        if match is not None:
            return match[1], match[2]
        else:
            match = re.search(vessel_voyage_regex3, text)
            if match is not None:
                return match[1], match[2]
            else:
                match = re.search(vessel_voyage_regex4, text)
                if match is not None:
                    return match[1], match[2]
                else:
                    match = re.search(vessel_only_regex, text)
                    if match is not None:
                        return match[1], None
                    else:
                        match = re.search(voyage_only_regex, text)
                        if match is not None:
                            return None, match[1]
    return None, None

def extract_eta_datetime(text):
    all_datetimes = nlp.search_all_datetimes(text)
    candiates = list()
    for tup in all_datetimes:
        begin_ind = tup[1]
        chars_before = text[max(begin_ind-50, 0):begin_ind]
        anchor_ind = chars_before.rfind("ETA")
        if anchor_ind == -1:
            anchor_ind = chars_before.rfind(" eta ")
            if anchor_ind == -1:
                anchor_ind = chars_before.rfind("eta")
                if anchor_ind != 0:
                    chars_before = chars_before.lower()
                    anchor_ind = chars_before.rfind("vessel arrival")
                    if anchor_ind == -1:
                        anchor_ind = chars_before.rfind("vsl arrival")
                        if anchor_ind == -1:
                            anchor_ind = chars_before.rfind("estimated arrival")
                            if anchor_ind == -1:
                                anchor_ind = chars_before.rfind("est. arrival")
                                if anchor_ind == -1:
                                    anchor_ind = chars_before.rfind("est arrival")
                                    if anchor_ind == -1:
                                        anchor_ind = chars_before.rfind("time of arrival")
                                        if anchor_ind == -1:
                                            anchor_ind = chars_before.rfind("date of arrival")
                                            if anchor_ind == -1:
                                                anchor_ind = chars_before.rfind("arrival date")
                                                if anchor_ind == -1:
                                                    anchor_ind = chars_before.rfind("arrival time")
                                                    if anchor_ind == -1:
                                                        anchor_ind = chars_before.rfind("vessel")
                                                        if anchor_ind == -1:
                                                            anchor_ind = chars_before.rfind("delay")
        if anchor_ind >= 0:
            candiates.append(tup)

    if len(candiates) == 0:
        return None, None
    elif len(candiates) == 1:
        if candiates[0][0] == "date":
            return candiates[0], None
        else:
            return None, candiates[0]
    else:
        candiates = sorted(candiates, key=lambda tup: tup[1])
        tup1 = candiates[0]
        tup2 = candiates[1]
        if (tup1[0] == "date") and (tup2[0] == "time"):
            return tup1, tup2
        else:
            if (text.find(" to ", tup1[2], tup2[1]) > 0) or (tup2[4] == "to"):
                if tup2[0] == "date":
                    return tup2, None
                else:
                    return None, tup2
            else:
                if tup1[0] == "date":
                    return tup1, None
                else:
                    return None, tup1


def is_useful(line_text):
    if line_text.find("You can view the Haulier Job here:") == 0:
        return False
    elif line_text.find("You can view the PSA Job here:") == 0:
        return False
    elif line_text.find("New Job Created by ") == 0:
        return False
    elif line_text.find("We care about you! Customers are our Priority") == 0:
        return False
    elif line_text.find("T: +65 6505 9675 F: +65 6327 7040 E: desmond") == 0:
        return False
    elif (line_text.find("CAUTION: ") >= 0) or (line_text.find("EXTERNAL EMAIL: ") >= 0):
        return False
    elif (line_text == "Importance: HIGH") or (line_text == "Importance: High"):
        return False
    elif (line_text.find("<") == 0) and (line_text.find(">") > 0):
        return False
    else:
        return True


def is_closing_statement(line_text, line_lower, n_parts):
    if n_parts > 5:
        return False
    elif (line_lower.find("regard") >= 0) or (line_text.find("Rgds") >= 0):
        return True
    elif line_lower.find("sincerely") >= 0:
        return True
    elif line_lower.find("cheers") >= 0:
        return True
    elif (line_text.find("Alvin Ea") == 0) or (line_text.find("CEO") == 0):
        return True
    elif ((line_lower.find("thank") >= 0) or (line_lower.find("tks") >= 0)) and (line_lower.find("for") == -1):
        return True
    else:
        return False


def is_greeting_statement(line_text, line_lower, n_parts):
    if n_parts > 6:
        return False
    elif (line_lower.find("hi ") == 0) or (line_lower.find("hi,") == 0):
        return True
    elif line_lower.find("dear ") == 0:
        return True
    elif line_lower.find("good morning") == 0:
        return True
    elif line_lower.find("good afternoon") == 0:
        return True
    elif line_lower.find("good evening") == 0:
        return True
    elif line_lower.find("good day") == 0:
        return True
    else:
        return False


BIG_SPACES = ["          ", "         ", "        ", "       ", "      ", "     ", "    ", "   ", "  "]
BIG_TABS = ["\t\t\t\t\t", "\t\t\t\t", "\t\t\t", "\t\t"]
MANY_FORWARDS = [">>>>>>>", ">>>>>>", ">>>>>", ">>>>", ">>>"]


def touch_up_line(line_text):
    # if line_text.find("So the total trucking cost will be") >= 0:
    #     raise Exception(line_text)
    string = line_text.strip(">").strip("-").strip().strip("\t").strip("\r").strip("*")
    string = string.replace(";", ",")
    string = string.replace("40’", "40'").replace("20’", "20'").replace("45’", "45'").replace("x40", " x 40").replace("x20", " x 20").replace("x45", " x 45").replace("X40", " x 40").replace("X20", " x 20").replace("X45", " x 45").replace("/40'", " x 40'").replace("/20'", " x 20'").replace("/45'", " x 45'")
    for spc in BIG_SPACES:
        string = string.replace(spc, " ")
    for tab in BIG_TABS:
        string = string.replace(tab, "\t")
    for forward in MANY_FORWARDS:
        string = string.replace(forward, " ")
    string = string.replace(" >> ", " to ")
    string = string.replace("Pls ", "Please ").replace("pls ", "please ").replace("Pleas ", "Please ").replace("Pl ", "Please ")
    string = string.replace("Cntr", "Container").replace("cntr", "container")
    string = string.replace("PteLtd", "Pte Ltd").replace("PTE.LTD", "PTE. LTD.")

    return string


def replace_line_patterns(line_text):
    string = line_text

    for match in re.findall("\w[\-/]{1,2}\s", string):
        string = string.replace(match, match[:1] + " " + match[1:])
    for match in re.findall("\w[\-/]$", string):
        string = string[:-1] + " " + string[-1:]
    for match in re.findall("\s[\*\-/@]\w", string):
        string = string.replace(match, match[:2] + " " + match[2:])
    for match in re.findall("^\d\.\w", string):
        string = string[:2] + " " + string[2:]
    for match in re.findall("(?i)\d+days|hours", string):
        string = string[:2] + " " + string[2:]
    for match in re.findall("(?i)\d+days", string):
        string = string.replace(match, match[:-4] + " " + match[-4:])
    for match in re.findall("(?i)\d+hours", string):
        string = string.replace(match, match[:-5] + " " + match[-5:])

    for dt in nlp.search_all_datetimes(string):
        if dt[0] == "date":
            string = string.replace(dt[3], "_DATE_")
        else:
            string = string.replace(dt[3], "_TIME_")
    for job_code in re.findall(job_code_regex, string):
        string = string.replace(job_code, "_JOB_CODE_")
    for cont_no in re.findall(container_no_regex, string):
        string = string.replace(cont_no, "_CONT_NO_")
    for money in re.findall(money_regex, string):
        string = string.replace(money, "_MONEY_")
    for postal in re.findall(postal_regex, string):
        string = string.replace(postal, "_POSTAL_")
    for tel in re.findall(tel_regex, string):
        string = string.replace(tel, "_TEL_")
    for mailto in re.findall(mailto_regex, string):
        string = string.replace(mailto, "_EMAIL_")
    for email in re.findall(email_regex, string):
        string = string.replace(email, "_EMAIL_")
    for url in re.findall(url_regex, string):
        string = string.replace(url, "_URL_")
    # vessel, voyage = extract_vessel_voyage(string)
    # if vessel is not None:
    #     string = string.replace(vessel, "_VESSEL_")
    # if voyage is not None:
    #     string = string.replace(voyage, "_CODE_")
    for code in re.findall(num_code_regex, string):
        string = string.replace(code, "_CODE_")
    for code in re.findall(complex_code_regex, string):
        string = string.replace(code, "_CODE_")

    # if string.find("_TIME_-TSO-_POSTAL_") >= 0:
    #     raise Exception(line_text)
    return string


def replace_doc_patterns(doc_text):
    string = doc_text

    vessel, voyage = extract_vessel_voyage(string)
    if vessel is not None:
        string = string.replace(vessel, "_VESSEL_")
    if voyage is not None:
        string = string.replace(voyage, "_CODE_")

    return string


bodies = {}
for b, body in enumerate(raw_email_data["body"].values):
    if type(body) == str:
        docs = list()
        current_doc = {"sender": raw_email_data.iat[b, 4], "lines": list(), "replaced_lines": list(), "new": True}
        docs.append(current_doc)
        bodies[b] = docs
        last_sender = ""
        for line in body.split("\n"):
            line_str = line.strip().strip("*")
            line_lower = line.lower().strip().strip("*")
            parts = line_lower.split(" ")
            n_parts = len(parts)
            if current_doc is None:
                if (line_str.find("From: ") == 0) or (line_str.find("发件人: ") == 0):
                    temp = nlp.search_pattern(line_str.lower(), email_regex)
                    if temp is not None:
                        last_sender = temp
                elif (line_str.find("Subject: ") == 0) or (line_str.find("主题: ") == 0):
                    current_doc = {"sender": last_sender, "lines": list(), "replaced_lines": list(), "new": False}
                    docs.append(current_doc)
                elif is_greeting_statement(line_str, line_lower, n_parts):
                    current_doc = {"sender": last_sender, "lines": list(), "replaced_lines": list(), "new": False}
                    docs.append(current_doc)
            else:
                if is_greeting_statement(line_str, line_lower, n_parts):
                    pass
                elif line_lower.find("_________________") == 0:
                    pass
                elif line_lower.find("===") == 0:
                    current_doc["lines"].append("\n")
                elif is_closing_statement(line_str, line_lower, n_parts):
                    current_doc = None
                    last_sender = ""
                elif line_str.find("Sent from ") == 0:
                    current_doc = None
                    last_sender = ""
                elif (line_str.find("From: ") == 0) or (line_str.find("发件人: ") == 0):
                    current_doc = None
                    temp = nlp.search_pattern(line_str.lower(), email_regex)
                    if temp is not None:
                        last_sender = temp
                elif (line_str == ":") and (len(current_doc["lines"]) > 0):
                    doc_lines = current_doc["lines"]
                    doc_lines[len(doc_lines) - 1] += line
                elif (line_str != "") and is_useful(line_str):
                    touched = touch_up_line(line_str)
                    if touched != "":
                        current_doc["lines"].append(touched)
                        current_doc["replaced_lines"].append(replace_line_patterns(touched))


with open("data/word2vec_data.txt", "w") as f:
    for b in bodies:
        for doc in bodies[b]:
            for l, line in enumerate(doc["replaced_lines"]):
                f.write(line + "\n")
                # if line.find("truck to 46 LAKESHORE VIEW, SANTOSA COVE") > 0:
                #     print(doc["lines"][l])
            break
        f.write("\n")


with open("data/bodies.pickle", "wb") as f:
    pickle.dump(bodies, f)


kk = set()
for bkey in bodies:
    first_doc = bodies[bkey][0]
    doc_text = "\n".join(first_doc["lines"])
    cand = extract_eta_datetimes(doc_text)
    if len(cand) > 0:
        kk.add(doc_text)


kk = set()
for bkey in bodies:
    first_doc = bodies[bkey][0]
    for l, line in enumerate(first_doc["replaced_lines"]):
        if ((line.lower().find("arrival date") >= 0) or (line.lower().find("date of arrival") >= 0)) and ((line.find("_DATE_") >= 0) or (line.find("_TIME_") >= 0)):
            kk.add(line)
len(kk)
kk
