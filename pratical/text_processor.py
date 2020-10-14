import numpy as np
import pandas as pd
from datetime import datetime
import re
import pickle

from lmpylib.core import *
from lmpylib import nlp

from gensim.corpora import Dictionary

import torch
from torch import nn, tensor
from torch.nn import functional as F

import nltk
from nltk import word_tokenize, sent_tokenize
from nltk.corpus import stopwords

import spacy

from transformers import BertTokenizer, BertModel

container_no_labels = ["container no.", "container no", "container num"]
delivery_addr_labels = ["delivery address", "address", "delivery addr", "addr", "delivery location", "location", "delivery loc", "loc", "deliver to", "delivery to"]
eta_date_labels = ["eta", "vessel arrival", "vsl arrival", "estimated arrival", "est arrival", "time of arrival", "date of arrival", "arrival", "vessel date", "vessel time", "vsl date", "vsl time"]
truckin_date_labels = ["truck-in", "truck in", "trucking-in", "trucking in"]
truckout_date_labels = ["truck-out", "truck out", "trucking-out", "trucking out", "return"]

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

vessel_part_no_digit_cs = "((?-i:[A-Z])[a-z\-@]*(?: (?-i:[A-Z])[a-z\-@]*)*|TBC|TBA|to be confirmed)"
# vessel_part_no_digit_ci = "([A-Za-z\-@]+(?: [A-Za-z\-@]+)*|TBC|TBA|to be confirmed)"
vessel_part_gen_cs = "((?-i:[A-Z])[\w\-@]*(?: (?-i:[A-Z\d])[\w\-@]*)*|TBC|TBA|to be confirmed)"
vessel_part_gen_ci = "([\w\-@]+(?: [\w\-@]*)*|TBC|TBA|to be confirmed)"
vsl_lbl_part = "(?:barge name|barge to|barge|vessel name|vessel|vsl name|vsl)\s*(?:actually |in fact )?(?:\:|should be|would be|will be|is called|is|are)?(?: actually| in fact)?\s*"
labelled_vessel_part_no_digit_cs = vsl_lbl_part + vessel_part_no_digit_cs
# labelled_vessel_part_no_digit_ci = vsl_lbl_part + vessel_part_no_digit_ci
labelled_vessel_part_gen_ci = vsl_lbl_part + vessel_part_gen_ci
labelled_vessel_part_gen_cs = vsl_lbl_part + vessel_part_gen_cs
voyage_part = "((?:\d[\w\-]{1,5})|(?:[\w\-]{0,5}\d[\w\-]{0,5})|(?:[\w\-]{1,5}\d)|TBC|TBA|to be confirmed)"
voy_lbl_part = "(?:v\.|v\s|voyage no.|voyage no|voyage number|voyage|voy. no.|voy. no|voy. number|voy.|voy no.|voy no|voy number|voy)\s*(?:actually |in fact )?(?:\:|should be|would be|will be|is|are)?(?: actually| in fact)?\s*"
labelled_voyage_part = voy_lbl_part + voyage_part
vessel_voyage_regex1 = "(?i)" + labelled_vessel_part_gen_cs + "[,\.]?\s*" + labelled_voyage_part + "(?:[,\.\s]|$)"      # e.g. vessel Titanic 88 voy 123S
vessel_voyage_regex2 = "(?i)" + labelled_vessel_part_no_digit_cs + "[,\.\s]" + voyage_part + "(?:[,\.\s]|$)"               # e.g. vessel Titanic 77S
vslvoy_comb_lbl_part = "(?:(?:barge|vessel name|vessel|vsl name|vsl)\s?[/,]\s?(?:v\.|v\s|voyage no.|voyage no|voyage number|voyage|voy. no.|voy. no|voy. number|voy.|voy no.|voy no|voy number|voy))\s*(?:actually |in fact )?(?:\:|should be|would be|will be|is|are)?(?: actually| in fact)?\s*"
vessel_voyage_regex3 = "(?i)" + vslvoy_comb_lbl_part + vessel_part_gen_ci + "\s*[/,]\s*" + "(?:" + voy_lbl_part + ")?" + voyage_part + "(?:[,\.\s]|$)"      # e.g. vessel/voy: titanic 99/S343
vessel_voyage_regex4 = "(?i)" + vslvoy_comb_lbl_part + vessel_part_no_digit_cs + "\s+" + "(?:" + voy_lbl_part + ")?" + voyage_part + "(?:[,\.\s]|$)"        # e.g. vessel/voy: Titanic 66S
# vessel_only_regex = "(?i)" + labelled_vessel_part_gen + "(?:[,\.\n]|$)"
vessel_only_regex = "(?i)" + labelled_vessel_part_gen_cs + "(?:[,\.\s]|$)"
voyage_only_regex = "(?i)" + labelled_voyage_part + "(?:[,\.\s]|$)"

footer_part = "(?:'|’| ft|ft| footer|footer| foot|foot| feet|feet)"
ctnr_type_part = "(?:(?:/| /)?\s?\(?(GP|HC|RH|RF|OT|FR|FT|TK|MT|DG|ED|DR|BN|BB|AK|DA)\)?)"
spe_part = "(20|40|45)(?:" + footer_part + ctnr_type_part + "|" + ctnr_type_part + "|" + footer_part + "| container| box | ctnr)"
qty_spe_regex = "(?i)" + "(one|two|three|four|five|six|seven|eight|nice|ten|a|\d{1,3})(?:\s*X)?\s*" + spe_part + "(?:[,\.\s]|$)"
qty_regex = "(?i)" + "(one|two|three|four|five|six|seven|eight|nice|ten|an|a|\d{1,3})(?: (empty|laden|MT|LD|GP|HC|RH|RF|OT|FR|FT|TK|DG|ED|DR|BN|BB|AK|DA))? (?:containers|container|ctnr|boxes|box)(?:[,\.\s]|$)"
spe_regex = "(?i)" + spe_part + "(?:[,\.\s]|$)"
foot_size_regex = "(?i)(20|40|45)" + footer_part + "(?:[/,\.\s]|$)"

addr_comp_preceding = "(?:^|(?<=[\s\.,:<>]))"
core_unit_part = "B?\d+[A-Z]?\d?(?:[\-/]B?\d*[A-Z]?\d?){0,9}"
unit_part_regex = "(?:unit\s|suite\s|#)" + core_unit_part + "(?:\s?/\s?#" + core_unit_part + "){0,5}"
unit_building_regex = "(?i)" + addr_comp_preceding + "(" + unit_part_regex + ")(?:([\s,].*)|$)"
level_building_regex = "(?i)" + addr_comp_preceding + "((?:\d+(?:st|nd|rd|th)\s+)?(?:level|story|storey|floor|lv|basement)(?:\s+B?\d+[A-Za-z]?)?)(?:([\s,].*)|$)"

BIG_SPACES = ["          ", "         ", "        ", "       ", "      ", "     ", "    ", "   ", "  "]
BIG_TABS = ["\t\t\t\t\t", "\t\t\t\t", "\t\t\t", "\t\t"]
MANY_FORWARDS = [">>>>>>>", ">>>>>>", ">>>>>", ">>>>", ">>>"]

nltk.download('stopwords')


device = "cpu"


class Document:
    def __init__(self, ori_text, client_id=None, touched_lines=None, replaced_lines=None, replacement_log=None):
        self.ori_text = ori_text.replace("’", "'").replace("\"", "``")
        self.lower_text = self.ori_text.lower()
        self.client_id = client_id
        self.data = {"vessel": None, "voyage": None, "eta_date": None, "eta_time": None, "in_date": None, "in_time": None, "out_date": None,
                     "out_time": None, "qty": None, "foot_size": None, "cntr_type": None, "addr": [], "comp": None, "cntr_nums": [],
                     "job_codes": []}

        if (touched_lines is not None) and (replaced_lines is not None) and (replacement_log is not None):
            self.touched_lines = touched_lines
            self.replaced_lines = replaced_lines
            self.replacement_log = replacement_log
        else:
            self.touched_lines = list()
            self.replaced_lines = list()
            self.replacement_log = list()
            self._process()
        self.touched_text = "\n".join(self.touched_lines)
        self.replaced_text = "\n".join(self.replaced_lines)

    def _process(self):
        for line_str in self.ori_text.split("\n"):
            line_str = line_str.strip().strip("*")
            if is_useful(line_str):
                touched = touch_up_line(line_str)
                if touched != "":
                    self.touched_lines.append(touched)
                    self.replaced_lines.append(replace_line_patterns(touched, self.replacement_log))


class EmailMessage:
    def __init__(self, msg_text, sender):
        self.latest_doc = None
        self.doc_history = list()
        self._process(msg_text, sender)

    def _process(self, msg_text, sender):
        docs = list()
        current_doc = {
            "sender": sender,
            "lines": list(),
            "replaced_lines": list(),
            "replacement_log": list(),
            "new": True}
        docs.append(current_doc)
        last_sender = ""
        for line in msg_text.split("\n"):
            line_str = line.strip().strip("*")
            line_lower = line.lower().strip().strip("*")
            parts = line_lower.split(" ")
            n_parts = len(parts)
            if current_doc is None:
                if (line_str.find("From: ") == 0) or (line_str.find("发件人: ") == 0):
                    match = re.search(email_regex, line_str.lower())
                    if match is not None:
                        last_sender = match[0]
                elif (line_str.find("Subject: ") == 0) or (line_str.find("主题: ") == 0):
                    current_doc = {
                        "sender": last_sender,
                        "lines": list(),
                        "replaced_lines": list(),
                        "replacement_log": list(),
                        "new": False}
                    docs.append(current_doc)
                elif is_greeting_statement(line_str, line_lower, n_parts):
                    current_doc = {
                        "sender": last_sender,
                        "lines": list(),
                        "replaced_lines": list(),
                        "replacement_log": list(),
                        "new": False}
                    docs.append(current_doc)
            else:
                if is_greeting_statement(line_str, line_lower, n_parts):
                    pass
                elif line_lower.find("_________________") == 0:
                    pass
                elif line_lower.find("===") == 0:
                    current_doc["lines"].append("\n")
                elif is_closing_statement(line_str, line_lower, n_parts):
                    if len(current_doc["lines"]) == 0:
                        touched = touch_up_line(line_str)
                        if touched != "":
                            current_doc["lines"].append(touched)
                            current_doc["replaced_lines"].append(replace_line_patterns(touched, current_doc["replacement_log"]))
                    current_doc = None
                    last_sender = ""
                elif line_str.find("Sent from ") == 0:
                    current_doc = None
                    last_sender = ""
                elif (line_str.find("From: ") == 0) or (line_str.find("发件人: ") == 0):
                    current_doc = None
                    match = re.search(email_regex, line_str.lower())
                    if match is not None:
                        last_sender = match[0]
                elif (line_str == ":") and (len(current_doc["lines"]) > 0):
                    doc_lines = current_doc["lines"]
                    doc_lines[len(doc_lines) - 1] += line
                elif (line_str != "") and is_useful(line_str):
                    touched = touch_up_line(line_str)
                    if touched != "":
                        current_doc["lines"].append(touched)
                        current_doc["replaced_lines"].append(replace_line_patterns(touched, current_doc["replacement_log"]))
        for doc in docs:
            if len(doc["lines"]) > 0:
                self.doc_history.append(Document("\n".join(doc["lines"]), doc["sender"], doc["lines"], doc["replaced_lines"], doc["replacement_log"]))
            else:
                self.doc_history.append(Document("?"))
        self.latest_doc = self.doc_history[0]


def trim_stopwords(text, fore_stopwords, back_stopwords):
    if text is None:
        return None

    tokens = text.split(" ")
    trim_start = -1
    trim_end = -1
    for i in range(len(tokens)):
        if fore_stopwords.__contains__(tokens[i]):
            trim_start = i + 1
        else:
            break
    for i in range(len(tokens)-1, -1, -1):
        if back_stopwords.__contains__(tokens[i]):
            trim_end = i
        else:
            break
    if (trim_start == -1) and (trim_end == -1):
        return text
    elif (trim_start != -1) and (trim_end != -1):
        return " ".join(tokens[trim_start:trim_end])
    elif trim_start != -1:
        return " ".join(tokens[trim_start:])
    else:
        return " ".join(tokens[:trim_end])


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
    if (n_parts is not None) and (n_parts > 6):
        return False
    else:
        text = " ".join(word_tokenize(line_lower)[:6])
        return re.search("(?i)^({})(?:$|[\s\.;,\:\!])".format(
                "|".join(["hi", "hello", "any one", "dear", "hey", "good morning", "good afternoon", "good evening", "good day"])),
                text) is not None


def touch_up_line(line_text):
    # if line_text.find("So the total trucking cost will be") >= 0:
    #     raise Exception(line_text)
    string = line_text.strip(">").strip("-").strip().strip("\t").strip("\r").strip("*")
    string = string.replace(";", ",").replace("’", "'").replace("\"", "``")
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


def replace_line_patterns(line_text, replace_log):
    string = line_text

    # ABC123-\s ==> ABC123 -\s
    for match in re.findall("\w[\-/]{1,2}\s", string):
        string = string.replace(match, match[:1] + " " + match[1:])

    # ABC123-$ ==> ABC123 -$
    for match in re.findall("\w[\-/]$", string):
        string = string[:-1] + " " + string[-1:]

    # \s*ABC123 ==> \s* ABC123, \s-ABC123 ==> \s- ABC123, \s@ABC123 ==> \s@ ABC123
    for match in re.findall("\s[\*\-/@]\w", string):
        string = string.replace(match, match[:2] + " " + match[2:])

    # ^1.a ==> ^1. a
    for match in re.findall("^\d\.[A-Za-z]", string):
        string = string[:2] + " " + string[2:]

    # 2days|hours ==> 2 days|hours
    for match in re.findall("(?i)\d+days|hours", string):
        string = string[:2] + " " + string[2:]
    for match in re.findall("(?i)\d+days", string):
        string = string.replace(match, match[:-4] + " " + match[-4:])
    for match in re.findall("(?i)\d+hours", string):
        string = string.replace(match, match[:-5] + " " + match[-5:])

    for dt in nlp.search_all_datetimes(string):
        if dt[0] == "date":
            string = string.replace(dt[3], "_DATE_")
            replace_log.append(("_DATE_", dt[3]))
        else:
            string = string.replace(dt[3], "_TIME_")
            replace_log.append(("_TIME_", dt[3]))
    for job_code in re.findall(job_code_regex, string):
        string = string.replace(job_code, "_JOB_CODE_")
    for cont_no in re.findall(container_no_regex, string):
        string = string.replace(cont_no, "_CONT_NO_")
    for money in re.findall(money_regex, string):
        string = string.replace(money, "_MONEY_")
    for postal in re.findall(postal_regex, string):
        string = string.replace(postal, "_POSTAL_")
        replace_log.append(("_POSTAL_", postal))
    for unit in re.findall(unit_building_regex, string):
        string = string.replace(unit[0], "_UNIT_LEVEL_")
        replace_log.append(("_UNIT_LEVEL_", unit[0]))
    for lvl in re.findall(level_building_regex, string):
        string = string.replace(lvl[0], "_UNIT_LEVEL_")
        replace_log.append(("_UNIT_LEVEL_", lvl[0]))
    for tel in re.findall(tel_regex, string):
        string = string.replace(tel, "_TEL_")
    for mailto in re.findall(mailto_regex, string):
        string = string.replace(mailto, "_EMAIL_")
    for email in re.findall(email_regex, string):
        string = string.replace(email, "_EMAIL_")
    for url in re.findall(url_regex, string):
        string = string.replace(url, "_URL_")
    for code in re.findall(num_code_regex, string):
        string = string.replace(code, "_CODE_")
        replace_log.append(("_CODE_", code))
    for code in re.findall(complex_code_regex, string):
        string = string.replace(code, "_CODE_")
        replace_log.append(("_CODE_", code))

    return string


def token_casing_feature(token, return_one_hot=True):
    code, desc = 5, "others"
    any_cap_match = re.search("[A-Z]", token)
    if any_cap_match is None:
        code, desc = 1, "lower"
    else:
        any_lower_match = re.search("[a-z]", token)
        if any_lower_match is None:
            code, desc = 2, "cap"
        else:
            camel_match = re.search("^[A-Z][^A-Z]+$", token)
            if camel_match is not None:
                code, desc = 3, "camel"
            else:
                camel_match = re.search("^[A-Z][^A-Z]*[A-Z]+[^A-Z]+$", token)
                if camel_match is not None:
                    code, desc = 4, "camel2"

    if return_one_hot:
        vec = np.array([0, 0, 0, 0, 0], dtype=int)
        if code > 0:
            vec[code - 1] = 1
        return vec
    else:
        return code, desc


def token_type_feature(token, return_one_hot=True):
    code, desc = 8, "others"
    only_alpha_match = re.search("^[A-Za-z&]+$", token)
    if only_alpha_match is not None:
        code, desc = 1, "alpha"
    else:
        only_num_match = re.search("^-?\(?(\d{1,3},)*\d+(\.\d+)?\)?$", token)
        if only_num_match is not None:
            code, desc = 2, "number"
        else:
            alpha_num_match = re.search("^\w+$", token)
            if alpha_num_match is not None:
                code, desc = 3, "alpha_number"
            else:
                punc_match = re.search("^[{}<>\[\]\(\),\.\?\:;\"'\|\\\\!@#\$%^&\*_\-=\+]+$", token)
                if punc_match is not None:
                    code, desc = 4, "punc"
                else:
                    connected_match = re.search("^.+(?:-.+)+$", token)
                    if connected_match is not None:
                        code, desc = 5, "connected"
                    else:
                        tuple_match = re.search("^.+(?:/.+)+$", token)
                        if tuple_match is not None:
                            code, desc = 6, "tuple"
                        else:
                            braced_match = re.search("^(\(\w+\))|(\[\w+\])$", token)
                            if braced_match is not None:
                                code, desc = 7, "braced"
    if return_one_hot:
        vec = np.array([0, 0, 0, 0, 0, 0, 0, 0], dtype=int)
        if code > 0:
            vec[code - 1] = 1
        return vec
    else:
        return code, desc


def remap_tokens_to_text(tokens, original_text, include_end_pos=True, include_end_pos_as_pairs=False, token_mapper={}):
    mapped_positions = list()
    end_positions = list()
    search_from_pos = 0
    for token in tokens:
        mapped_pos = original_text.find(token, search_from_pos)
        if mapped_pos == -1:
            if (token_mapper is not None) and (token_mapper.__contains__(token)):
                token = token_mapper[token]
                mapped_pos = original_text.find(token, search_from_pos)
                if mapped_pos == -1:
                    raise Exception(
                        "tokens and the original text cannot be remapped, because the token '{}' is not found in the original text from position {} onwards:\n{}".format(
                            token, search_from_pos, original_text))
            else:
                raise Exception(
                    "tokens and the original text cannot be remapped, because the token '{}' is not found in the original text from position {} onwards. Consider using token_mapper argument to map the token to the original characters in the original text:\n{}".format(
                        token, search_from_pos, original_text))
        if mapped_pos > search_from_pos:
            space_match = re.search("^\s+$", original_text[search_from_pos:mapped_pos])
            if space_match is None:
                raise Exception(
                    "tokens and the original text cannot be remapped, because there is non-space between position {} and {} of the original text:\n{}".format(
                        search_from_pos, mapped_pos, original_text))
        mapped_positions.append(mapped_pos)
        end_positions.append(mapped_pos + len(token))
        search_from_pos = len(token) + mapped_pos
    if len(original_text) > search_from_pos:
        space_match = re.search("^\s+$", original_text[search_from_pos:])
        if space_match is None:
            raise Exception(
                "tokens and the original text cannot be remapped, because there is non-space from position {} onwards in the original text:\n".format(
                    search_from_pos))

    if include_end_pos:
        if include_end_pos_as_pairs:
            return [(mapped_positions[i], end_positions[i]) for i in range(len(mapped_positions))]
        else:
            return mapped_positions, end_positions
    else:
        return mapped_positions


def span_predictions_to_fragments(predictions, tokens, original_text, span_begin_class=1, span_intermidate_class=2, span_end_class=3,
                                  token_mapper={}, return_pos_pairs=False):
    assert len(predictions) == len(tokens), "predictions and tokens must have same length, but got {} and {}".format(len(predictions),
                                                                                                                     len(tokens))

    remapped_token_start_pos, remapped_token_end_pos = remap_tokens_to_text(tokens, original_text, token_mapper=token_mapper)

    frag_pos = list()
    start_pos, end_pos = None, None
    for t, pred in enumerate(predictions):
        if t == 0:
            if (pred == span_begin_class) or (pred == span_intermidate_class):
                start_pos = remapped_token_start_pos[t]
                end_pos = remapped_token_end_pos[t]
        elif t < len(tokens) - 1:
            if start_pos is not None:
                if (pred == span_intermidate_class) or (pred == span_end_class):
                    end_pos = remapped_token_end_pos[t]
                elif pred == span_begin_class:
                    frag_pos.append((start_pos, end_pos))
                    start_pos = remapped_token_start_pos[t]
                    end_pos = remapped_token_end_pos[t]
                else:
                    frag_pos.append((start_pos, end_pos))
                    start_pos, end_pos = None, None
            else:
                if (pred == span_begin_class) or (pred == span_intermidate_class):
                    start_pos = remapped_token_start_pos[t]
                    end_pos = remapped_token_end_pos[t]
        else:
            if start_pos is not None:
                if (pred == span_intermidate_class) or (pred == span_end_class):
                    end_pos = remapped_token_end_pos[t]
                    frag_pos.append((start_pos, end_pos))
                elif pred == span_begin_class:
                    frag_pos.append((start_pos, end_pos))
                    start_pos = remapped_token_start_pos[t]
                    end_pos = remapped_token_end_pos[t]
                    frag_pos.append((start_pos, end_pos))
                else:
                    frag_pos.append((start_pos, end_pos))
                    start_pos, end_pos = None, None
            else:
                if (pred == span_begin_class) or (pred == span_intermidate_class):
                    start_pos = remapped_token_start_pos[t]
                    end_pos = remapped_token_end_pos[t]
                    frag_pos.append((start_pos, end_pos))

    if not return_pos_pairs:
        return [original_text[pos[0]:pos[1]] for pos in frag_pos]
    else:
        return frag_pos


def my_word_tokenize(text):
    tokens = list()
    for token in word_tokenize(text):
        if (len(token) > 1) and ((token.find(",") == 0) or (token.find(".") == 0)):
            tokens.append(token[:1])
            tokens.append(token[1:])
        else:
            match = re.search("(.*[A-Za-z]),(\d.*)", token)
            if match is None:
                tokens.append(token)
            else:
                tokens.append(match[1])
                tokens.append(",")
                tokens.append(match[2])
    return tokens


def to_bert_uncased_friendly(text):
    text0 = text.replace("_DATE_", "on this date")
    text0 = text0.replace("_TIME_", "at this time")
    text0 = text0.replace("_JOB_CODE_", "the job code")
    text0 = text0.replace("_CODE_", "this code")
    text0 = text0.replace("_CONT_NO_", "this code")
    text0 = text0.replace("_MONEY_", "this much money")
    text0 = text0.replace("_POSTAL_", "postal code")
    text0 = text0.replace("_UNIT_LEVEL_", "level 1")
    text0 = text0.replace("_TEL_", "tel")
    text0 = text0.replace("_EMAIL_", "email")
    text0 = text0.replace("_URL_", "url")
    text0 = text0.lower()
    tok = np.asarray(my_word_tokenize(text0))
    tok = np.insert(tok, 0, "[CLS]")
    ind = (tok == ".") | (tok == ",") | (tok == "!") | (tok == "?") | (tok == ";")
    tok[ind] = "[SEP]"
    return " ".join(tok)


def gen_bert_embeddings(texts, padding=True, padding_min_len=None):
    bert_texts = [to_bert_uncased_friendly(txt) for txt in texts]

    tokenizer = BertTokenizer.from_pretrained('bert-large-uncased')
    bert_tokenized_texts = [tokenizer.wordpiece_tokenizer.tokenize(txt) for txt in bert_texts]
    bert_token_indices = [tokenizer.convert_tokens_to_ids(tokens) for tokens in bert_tokenized_texts]

    bert_model = BertModel.from_pretrained('bert-large-uncased')
    bert_model.eval()
    bert_model.to(device)

    if padding:
        sent_lengths = np.zeros(len(texts), dtype=int)
        for s in range(len(texts)):
            m = np.asarray(bert_tokenized_texts[s]) == "[SEP]"
            segments_ids = m.cumsum() - m

            tokens_tensor, segments_tensors = torch.tensor([bert_token_indices[s]]), torch.tensor([segments_ids])

            with torch.no_grad():
                encoded_layers, _ = bert_model(tokens_tensor.to(device), segments_tensors.to(device))
                sent_lengths[s] = encoded_layers.shape[1]
        max_len = np.max(sent_lengths)
        if padding_min_len is not None:
            max_len = max(max_len, padding_min_len)

        padded_bert_texts = [None] * len(texts)
        for i, l in enumerate(sent_lengths):
            padded = bert_texts[i]
            for p in range(max_len - l):
                padded += " [PAD]"
            padded_bert_texts[i] = padded

        bert_tokenized_texts = [tokenizer.wordpiece_tokenizer.tokenize(txt) for txt in padded_bert_texts]
        bert_token_indices = [tokenizer.convert_tokens_to_ids(tokens) for tokens in bert_tokenized_texts]

        embeddings = np.zeros((len(texts), max_len, 1024), dtype=np.float32)
        for s in range(len(texts)):
            m = np.asarray(bert_tokenized_texts[s]) == "[SEP]"
            segments_ids = m.cumsum() - m

            tokens_tensor, segments_tensors = torch.tensor([bert_token_indices[s]]), torch.tensor([segments_ids])

            with torch.no_grad():
                encoded_layers, _ = bert_model(tokens_tensor.to(device), segments_tensors.to(device))
                embeddings[s] = np.asarray(encoded_layers.cpu(), dtype=np.float32)
        return embeddings
    else:
        bert_tokenized_texts = [tokenizer.wordpiece_tokenizer.tokenize(txt) for txt in bert_texts]
        bert_token_indices = [tokenizer.convert_tokens_to_ids(tokens) for tokens in bert_tokenized_texts]

        embeddings = [None] * len(texts)
        for s in range(len(texts)):
            m = np.asarray(bert_tokenized_texts[s]) == "[SEP]"
            segments_ids = m.cumsum() - m

            tokens_tensor, segments_tensors = torch.tensor([bert_token_indices[s]]), torch.tensor([segments_ids])

            with torch.no_grad():
                encoded_layers, _ = bert_model(tokens_tensor.to(device), segments_tensors.to(device))
                embeddings[s] = np.asarray(encoded_layers.cpu(), dtype=np.float32)
        return embeddings


class EntityDataset(nn.Module):
    def __init__(self, texts, target_entity_name, use_vocab=''):
        assert (target_entity_name is None) or (type(target_entity_name) == str) or (
                    type(target_entity_name) == list), "target_entity_name must be either str, list or None."

        if (target_entity_name is not None) and (target_entity_name != ""):
            self.target_entity_names = target_entity_name
            self.set_tagged_text(texts)
        else:
            self.set_original_text(texts)
            self.target_entity_names = None

        # Initialize the vocab
        special_tokens = {'<pad>': 0, '<unk>': 1, '<s>': 2, '</s>': 3}
        if type(use_vocab) == str:
            with open(use_vocab) as fin:
                pretrained_keys = {line.strip(): i for i, line in enumerate(fin)}
            self.vocab = Dictionary({})
            self.vocab.token2id = pretrained_keys
            self.vocab_type = "pretrained"
            self.unknown_word_idx = self.vocab.token2id["?"]
        elif use_vocab is not None:
            self.vocab = use_vocab
            self.vocab_type = "reuse"
            self.vocab.patch_with_special_tokens(special_tokens)
            self.unknown_word_idx = 1
        else:
            self.vocab = Dictionary(self.tokenized_docs)
            self.vocab_type = "new"
            self.vocab.patch_with_special_tokens(special_tokens)
            self.unknown_word_idx = 1

        # Keep track of the vocab size.
        self.vocab_size = len(self.vocab)

    def set_tagged_text(self, tagged_texts):
        pass

    def set_original_text(self, doc_texts):
        self.ori_texts = doc_texts
        self.tokenized_docs = list()
        self.crafted_features = list()
        self.token_level_labels = None
        for doc in self.ori_texts:
            tokens = my_word_tokenize(doc)
            casing_features = np.array([token_casing_feature(token) for token in tokens])
            type_features = np.array([token_type_feature(token) for token in tokens])
            self.tokenized_docs.append(tokens)
            self.crafted_features.append(np.concatenate([casing_features, type_features], axis=1))

        self._len = len(self.ori_texts)
        self.max_len = max(len(doc) for doc in self.tokenized_docs) + 2

    def __getitem__(self, doc_index):
        doc = self.tokenized_docs[doc_index]
        vectorized_doc = self.vectorize(doc, unknown_word_idx=self.unknown_word_idx)
        doc_len = len(vectorized_doc)
        crafted_feat = self.crafted_features[doc_index]

        if self.vocab_type != "pretrained":
            pad_len = self.max_len - len(vectorized_doc)
            pad_dim = (0, pad_len)
            padded_vectorized_doc = F.pad(vectorized_doc, pad_dim, 'constant')
            padded_crafted_features = np.concatenate(
                [np.zeros((1, crafted_feat.shape[1])), crafted_feat, np.zeros((pad_len + 1, crafted_feat.shape[1]))])

            if self.token_level_labels is not None:
                padded_y = np.concatenate([[0], np.array(self.token_level_labels[doc_index], dtype=int) + 1, [0] * (pad_len + 1)])
                return {'x': padded_vectorized_doc,
                        'x_crafted': torch.tensor(padded_crafted_features, dtype=torch.float),
                        'y': tensor(padded_y, dtype=torch.long)}
            else:
                return {'x': padded_vectorized_doc,
                        'x_crafted': torch.tensor(padded_crafted_features, dtype=torch.float)}
        else:
            return None

    def __len__(self):
        return self._len

    def vectorize(self, doc_tokens, start_doc_idx=2, end_doc_idx=3, unknown_word_idx=1):
        if self.vocab_type != "pretrained":
            vectorized_doc = [start_doc_idx] + self.vocab.doc2idx(doc_tokens, unknown_word_index=unknown_word_idx) + [end_doc_idx]
        else:
            vectorized_doc = self.vocab.doc2idx(doc_tokens, unknown_word_index=unknown_word_idx)
        return torch.tensor(vectorized_doc)

    def unvectorize(self, indices):
        return [self.vocab[i] for i in indices]


class NerClassifier(nn.Module):
    def __init__(self, vocab_size, embedding_size, hidden_size, crafted_feat_size, classifier1_hidden_size, classifier2_hidden_size,
                 n_gru_layers, n_classes=5, bidirectionary_gru=False, gru_on_crafted_inputs=False, pretrained_embeddings=None):
        super(NerClassifier, self).__init__()

        self.gru_on_crafted_inputs = gru_on_crafted_inputs

        if pretrained_embeddings is None:
            self.embedding_layer = nn.Embedding(vocab_size, embedding_size, padding_idx=0)
        else:
            self.embedding_layer = nn.Embedding.from_pretrained(pretrained_embeddings)

        self.bidirectionary = bidirectionary_gru

        if gru_on_crafted_inputs:
            self.gru_layers = nn.GRU(
                input_size=embedding_size + crafted_feat_size,
                hidden_size=hidden_size,
                num_layers=n_gru_layers,
                bias=True,
                batch_first=True,
                dropout=0,
                bidirectional=bidirectionary_gru)
        else:
            self.gru_layers = nn.GRU(
                input_size=embedding_size,
                hidden_size=hidden_size,
                num_layers=n_gru_layers,
                bias=True,
                batch_first=True,
                dropout=0,
                bidirectional=bidirectionary_gru)

        if gru_on_crafted_inputs:
            self.classifier_layer1 = nn.Linear(hidden_size * (2 if self.bidirectionary else 1), classifier1_hidden_size)
        else:
            self.classifier_layer1 = nn.Linear(hidden_size * (2 if self.bidirectionary else 1) + crafted_feat_size, classifier1_hidden_size)

        self.classifier_layer2 = nn.Linear(classifier1_hidden_size, classifier2_hidden_size)

        self.classifier_layer3 = nn.Linear(classifier2_hidden_size, n_classes)

    def forward(self, token_inputs, crafted_inputs, dropout=True):
        # vocab_size: V
        # embed_size: E
        # hidden_size: H
        # num_layers: L
        # num_directions: Dir
        # sequence_len: Seq = max_sent_len-1
        # batch_size: n

        # single in-shape:   (, Seq) one-hot~>    (Seq, V) ==> via x embedding_weights:(V, E) ==>     (Seq, E)
        # batched in-shape: (n, Seq) one-hot~> (n, Seq, V) ==> via x embedding_weights:(V, E) ==>  (n, Seq, E)
        embedded = self.embedding_layer(token_inputs)

        if self.gru_on_crafted_inputs:
            if len(embedded.shape) == 2:
                # single sentence
                # in-shape (Seq, E) + (Seq, Craft) ==> (1*Seq, E+Craft)
                gru_inputs = torch.cat([embedded, crafted_inputs], dim=1)

                # in-shape (input, initial): (Seq, E+Craft), (L*Dir, H) ==> (Seq, H*Dir), (L*Dir, H)
                gru_output, final_hidden_states = self.gru_layers(gru_inputs, None)
            else:
                # batched sentences
                # in-shape (n, Seq, E)  + (n, Seq, Craft) ==> (n, Seq, E+Craft)
                gru_inputs = torch.cat([embedded, crafted_inputs], dim=2)

                # in-shape (input, initial): (n, Seq, E+Craft), (L*Dir, n, H) ==> (n, Seq, H*Dir), (L*Dir, n, H)
                gru_output, final_hidden_states = self.gru_layers(gru_inputs, None)
        else:
            # single sentence
            # in-shape (input, initial): (Seq, E), (L*Dir, H) ==> (Seq, H*Dir), (L*Dir, H)
            #
            # batched sentences
            # in-shape (input, initial): (n, Seq, E), (L*Dir, n, H) ==> (n, Seq, H*Dir), (L*Dir, n, H)
            gru_output, final_hidden_states = self.gru_layers(embedded, None)
            # gru_output: final GRU output, for each token in each sentence, of the last layer
            # final_hidden_states: final hidden states, for each sentence as a whole, of each layer

        mini_batch, sequence_len, directional_hidden_size = gru_output.shape

        # Apply dropout.
        # if the data size is relatively small, the dropout rate can be higher. normally 0.1~0.8
        learned_features = F.dropout(gru_output, 0.5 if dropout else 0)

        if self.gru_on_crafted_inputs:
            # (n, Seq, H*Dir) ==> (n*Seq, H*Dir)
            classification_inputs = learned_features.contiguous().view((mini_batch * sequence_len, -1))
        else:
            if len(learned_features.shape) == 2:
                # single in-shape:     (Seq, H*Dir) + (Seq, Craft) ==> (1*Seq, H*Dir+Craft)
                classification_inputs = torch.cat([learned_features, crafted_inputs], dim=1)
            else:
                # batched in-shape: (n, Seq, H*Dir) + (n, Seq, Craft) ==> (n, Seq, H*Dir+Craft)
                classification_inputs = torch.cat([learned_features, crafted_inputs], dim=2)

                # (n, Seq, H*Dir+Craft) ==> (n*Seq, H*Dir+Craft)
                classification_inputs = classification_inputs.contiguous().view((mini_batch * sequence_len, -1))

                # Put it through the classifier
        # single in-shape:  (1*Seq, H*Dir+Craft?) ==> via x classifier_weights:(H*Dir+Craft?, classifier1_hid) ==> (1*Seq, classifier1_hid)
        # batched in-shape: (n*Seq, H*Dir+Craft?) ==> via x classifier_weights:(H*Dir+Craft?, classifier1_hid) ==> (n*Seq, classifier1_hid)
        dense = self.classifier_layer1(classification_inputs)
        dense = self.classifier_layer2(dense)
        output = self.classifier_layer3(dense).view(mini_batch, sequence_len, -1)

        # single out-shape:    (1, Seq, n_classes)
        # batched out-shape:   (n, Seq, n_classes)
        log_probs = F.log_softmax(output, dim=2)
        return log_probs


def sigmoid(x):
    return 1 / (1 + np.exp(-x))


def predict_book_intent(doc, include_stacked=False):
    # with open("models/book_intent_padded_bert_svm.pickle", "rb") as f:
    #     padded_bert_svm = pickle.load(f)
    # embeddings = gen_bert_embeddings(doc.replaced_lines, padding=True, padding_min_len=169)
    # embeddings = np.mean(embeddings, axis=1)
    # padded_bert_svm_predicts = padded_bert_svm.predict(embeddings)

    with open("models/book_intent_naive_bayes.pickle", "rb") as f:
        nb_model = pickle.load(f)
    with open("models/book_intent_naive_bayes_vectorizer.pickle", "rb") as f:
        vectorizer = pickle.load(f)
    vectors = vectorizer.transform(doc.replaced_lines)
    nb_predicts = nb_model.predict(vectors)

    with open("models/book_intent_ngram_lbfgs_lr.pickle", "rb") as f:
        lr_model = pickle.load(f)
    with open("models/book_intent_ngram_lbfgs_lr_vectorizer.pickle", "rb") as f:
        vectorizer = pickle.load(f)
    vectors = vectorizer.transform(doc.replaced_lines)
    prob = sigmoid(lr_model.decision_function(vectors))
    lr_predicts = (prob > 0.25).astype(int)

    # stacked = np.stack([padded_bert_svm_predicts, nb_predicts, lr_predicts])
    stacked = np.stack([lr_predicts, nb_predicts, lr_predicts])
    predict_for_lines = np.round(np.mean(stacked, axis=0), 2)

    if include_stacked:
        return np.max(predict_for_lines), stacked
    else:
        return np.max(predict_for_lines)


def predict_update_intent(doc, include_stacked=False):
    predictable_lines = doc.replaced_lines
    if len(predictable_lines) > 0:
        with open("models/update_intent_naive_bayes.pickle", "rb") as f:
            nb_model = pickle.load(f)
        with open("models/update_intent_naive_bayes_vectorizer.pickle", "rb") as f:
            vectorizer = pickle.load(f)
        vectors = vectorizer.transform(predictable_lines)
        nb_predicts = nb_model.predict(vectors)

        with open("models/update_intent_cls_lr.pickle", "rb") as f:
            lr_model = pickle.load(f)
        with open("models/update_intent_cls_lr_vectorizer.pickle", "rb") as f:
            vectorizer = pickle.load(f)
        vectors = vectorizer.transform(predictable_lines)
        prob = sigmoid(lr_model.decision_function(vectors))
        lr_predicts = (prob > 0.4).astype(int)

        with open("models/update_intent_clf_forest.pickle", "rb") as f:
            forest_model = pickle.load(f)
        with open("models/update_intent_clf_forest_vectorizer.pickle", "rb") as f:
            vectorizer = pickle.load(f)
        vectors = vectorizer.transform(predictable_lines)
        forest_predicts = forest_model.predict(vectors)

        stacked = np.stack([forest_predicts, nb_predicts, lr_predicts])
        predict_for_lines = np.round(np.mean(stacked, axis=0), 2)

        if include_stacked:
            return np.max(predict_for_lines), stacked
        else:
            return np.max(predict_for_lines)

    elif include_stacked:
        return 0, None
    else:
        return 0


def extract_vessel_voyage(doc):

    invalid_vsl_name_regex = "(?i)(?:^|before |bfr |after |aft |between |from |frm |than |as of |at |on |to |by |since |till |next |coming |this |last |@ |@)(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun|January|February|March|April|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)$"
    voy_validation_regex = "([A-Z]\d{1,9})|(\d{1,9}[A-Z]|TBC|TBA|to be confirmed)"

    text = doc.ori_text
    fore_stopwords = set(stopwords.words('english'))
    fore_stopwords.remove("the")
    back_stopwords = set(stopwords.words('english'))

    match = re.search(vessel_voyage_regex1, text)
    if match is not None:
        vsl, voy = trim_stopwords(match[1], fore_stopwords, back_stopwords), match[2]
        match_vsl = re.search(invalid_vsl_name_regex, vsl)
        match_voy = re.search(voy_validation_regex, voy)
        if (match_vsl is None) and (match_voy is not None):
            return vsl, voy

    match = re.search(vessel_voyage_regex2, text)
    if match is not None:
        vsl, voy = trim_stopwords(match[1], fore_stopwords, back_stopwords), match[2]
        match_vsl = re.search(invalid_vsl_name_regex, vsl)
        match_voy = re.search(voy_validation_regex, voy)
        if (match_vsl is None) and (match_voy is not None):
            return vsl, voy

    match = re.search(vessel_voyage_regex3, text)
    if match is not None:
        vsl, voy = trim_stopwords(match[1], fore_stopwords, back_stopwords), match[2]
        match_vsl = re.search(invalid_vsl_name_regex, vsl)
        match_voy = re.search(voy_validation_regex, voy)
        if (match_vsl is None) and (match_voy is not None):
            return vsl, voy

    match = re.search(vessel_voyage_regex4, text)
    if match is not None:
        vsl, voy = trim_stopwords(match[1], fore_stopwords, back_stopwords), match[2]
        match_vsl = re.search(invalid_vsl_name_regex, vsl)
        match_voy = re.search(voy_validation_regex, voy)
        if (match_vsl is None) and (match_voy is not None):
            return vsl, voy

    match = re.search(vessel_only_regex, text)
    if match is not None:
        vsl = trim_stopwords(match[1], fore_stopwords, back_stopwords)
        match_vsl = re.search(invalid_vsl_name_regex, vsl)
        if match_vsl is not None:
            vsl = None
    else:
        vsl = None

    match = re.search(voyage_only_regex, text)
    if match is not None:
        voy = match[1]
        match_voy = re.search(voy_validation_regex, voy)
        if match_voy is None:
            voy = None
    else:
        voy = None

    return vsl, voy


def extract_qty_spe(doc):
    text = doc.ori_text
    match = re.search(qty_spe_regex, text)
    if match is not None:
        if match[3] is None:
            return match[1], match[2], match[4]
        else:
            return match[1], match[2], match[3]

    match = re.search(qty_regex, text)
    if match is not None:
        qty, foot_size, ctnr_type = match[1], None, match[2]
    else:
        qty, foot_size, ctnr_type = None, None, None

    match = re.search(spe_regex, text)
    if match is not None:
        if foot_size is None:
            foot_size = match[1]
        if ctnr_type is None:
            if match[2] is not None:
                ctnr_type = match[2]
            else:
                ctnr_type = match[3]

    if foot_size is None:
        match = re.search(foot_size_regex, text)
        if match is not None:
            foot_size = match[1]

    return qty, foot_size, ctnr_type


def process_datetime_candidates(candidates, text):
    if len(candidates) == 0:
        return None, None
    elif len(candidates) == 1:
        if candidates[0][0] == "date":
            return candidates[0], None
        else:
            return None, candidates[0]
    elif len(candidates) == 2:
        candidates = sorted(candidates, key=lambda tup: tup[1])
        tup1 = candidates[0]
        tup2 = candidates[1]
        if (tup1[0] == "date") and (tup2[0] == "time"):
            return tup1, tup2
        else:
            if (tup2[4] == "to") or (re.search("( to |but |instead(,| it))", text[tup1[2]:tup2[1]]) is not None):
                if tup2[0] == "date":
                    return tup2, None
                else:
                    return None, tup2
            else:
                if tup1[0] == "date":
                    return tup1, None
                else:
                    return None, tup1
    elif len(candidates) == 4:
        candidates = sorted(candidates, key=lambda tup: tup[1])
        tup1 = candidates[0]
        tup2 = candidates[1]
        tup3 = candidates[2]
        tup4 = candidates[3]

        if ((tup3[4] == "to") or (re.search("( to |but |instead(,| it))", text[tup2[2]:tup3[1]]) is not None)) and (tup3[0] == "date") and (tup4[0] == "time"):
            return tup3, tup4
        elif tup1[0] == "date":
            return tup1, None
        elif tup2[0] == "date":
            return tup2, None
        elif tup3[0] == "date":
            return tup3, None
        elif tup4[0] == "date":
            return tup4, None
        else:
            return None, None
    else:
        candidates = sorted(candidates, key=lambda tup: tup[1])
        tup1 = candidates[0]
        tup2 = candidates[1]
        tup3 = candidates[2]

        if (tup2[4] == "to") or (re.search("( to |but |instead(,| it))", text[tup1[2]:tup2[1]]) is not None):
            if (tup1[0] == "date") and (tup2[0] == "date") and (tup3[0] == "time"):
                return tup2, tup3
            elif tup2[0] == "date":
                return tup2, None
            elif tup3[0] == "date":
                return tup3, None
            elif tup1[0] == "date":
                return tup1, None
            else:
                return None, None
        elif (tup3[4] == "to") or (re.search("( to |but |instead(,| it))", text[tup2[2]:tup3[1]]) is not None):
            if (tup1[0] == "date") and (tup2[0] == "time") and (tup3[0] == "date"):
                return tup3, tup2
            elif (tup1[0] == "date") and (tup2[0] == "time") and (tup3[0] == "time"):
                return tup1, tup3
            elif tup3[0] == "date":
                return tup3[0], None
            elif tup3[0] == "time":
                return None, tup3[0]
            else:
                return None, None
        else:
            if (tup1[0] == "date") and (tup2[0] == "time"):
                return tup1, tup2
            elif (tup2[0] == "date") and (tup3[0] == "time"):
                return tup2, tup3
            elif tup1[0] == "date":
                return tup1, None
            elif tup2[0] == "date":
                return tup2, None
            elif tup3[0] == "date":
                return tup3, None
            else:
                return None, None


def extract_eta_datetime(doc, get_whatever_date_found=False):
    text = doc.ori_text
    candidates = list()

    match = re.search("(?i)est\. arrival", text)
    if match is not None:
        text = text.replace(match[0], "est arrival")

    sent_begin_indices = list()
    last_sent_end_ind = 0
    for sent in sent_tokenize(text):
        ind = text.find(sent, last_sent_end_ind)
        sent_begin_indices.append(ind)
        last_sent_end_ind = ind + len(sent)
    sent_begin_indices = np.array(sent_begin_indices)

    all_datetimes = nlp.search_all_datetimes(text)
    for tup in all_datetimes:
        tup_begin_ind = tup[1]
        sent_begin_ind = sent_begin_indices[sent_begin_indices <= tup_begin_ind][-1]
        chars_before = text[max(sent_begin_ind, tup_begin_ind - 100):tup_begin_ind]
        anchor_ind = chars_before.rfind("ETA")
        if anchor_ind == -1:
            anchor_ind = chars_before.rfind(" eta ")
            if anchor_ind == -1:
                anchor_ind = chars_before.rfind("eta")
                if anchor_ind != 0:
                    chars_before = chars_before.lower()
                    for keyword in ["vessel arrival", "vsl arrival", "estimated arrival", "est arrival", "time of arrival",
                                    "date of arrival", "arrival date", "arrival time", "vessel", "vsl", "barge"]:
                        anchor_ind = chars_before.rfind(keyword)
                        if anchor_ind >= 0:
                            break

        if anchor_ind >= 0:
            candidates.append(tup)

    if get_whatever_date_found and (len(candidates) == 0) and (len(all_datetimes) > 0):
        candidates = all_datetimes[:2]

    candidates = [c for c in candidates if (c[4] != "not") and (c[4] != "n't")]

    if len(candidates) > 0:
        return process_datetime_candidates(candidates, text)
    else:
        match = re.search(
            "(?i)(" + "|".join(eta_date_labels) + ")(?:\s+(?:date|time))?\s*(?:\:|is)?\s*((?-i:TBC)|(?-i:TBA)|to be confirmed)",
            text)
        if match is not None:
            ind = text.find(match[0])
            return ('date', ind, ind + len(match[0]), None, None, None, None, 'To Be Confirmed'), None
        else:
            return None, None


def extract_truckin_datetime(doc, get_whatever_date_found=False):
    text = doc.ori_text
    candidates = list()

    sent_begin_indices = list()
    last_sent_end_ind = 0
    for sent in sent_tokenize(text):
        ind = text.find(sent, last_sent_end_ind)
        sent_begin_indices.append(ind)
        last_sent_end_ind = ind + len(sent)
    sent_begin_indices = np.array(sent_begin_indices)

    all_datetimes = nlp.search_all_datetimes(text)
    for tup in all_datetimes:
        tup_begin_ind = tup[1]
        sent_begin_ind = sent_begin_indices[sent_begin_indices <= tup_begin_ind][-1]
        chars_before = text[max(sent_begin_ind, tup_begin_ind - 100):tup_begin_ind]

        chars_before = chars_before.lower()
        for keyword in ["truck-in", "truck in", "trucking-in", "trucking in", "send in", "put in", "pull in", "pull out", "arrange", "deliver", "send", "deploy",
                        "collect", "order", "book", "put", "need", "require", "want", "expect", "container", "ctnr", "box"]:
            anchor_ind = chars_before.rfind(keyword)
            if anchor_ind >= 0:
                break

        if anchor_ind == -1:
            chars_before = text[max(sent_begin_ind, tup_begin_ind - 100):tup_begin_ind]
            for keyword in ["GP", "HC", "RH", "RF"]:
                anchor_ind = chars_before.rfind(keyword)
                if anchor_ind >= 0:
                    break

        if anchor_ind >= 0:
            candidates.append(tup)

    if get_whatever_date_found and (len(candidates) == 0) and (len(all_datetimes) > 0):
        candidates = all_datetimes[:2]
    # if get_whatever_date_found and (len(candidates) == 0):
    #     if (doc.lower_text.find("asap") < 30) or (doc.lower_text.find("now") < 30) or (doc.lower_text.find("immediately") < 30):
    #         return ('date', 0, 0, None, None, None, None, 'today'), ('time', 0, 0, None, None, None, None, 'now')

    candidates = [c for c in candidates if (c[4] != "not") and (c[4] != "n't")]

    if len(candidates) > 0:
        return process_datetime_candidates(candidates, text)
    else:
        match = re.search("(?i)(" + "|".join(truckin_date_labels) +  ")(?:\s+(?:date|time))?\s*(?:\:|is)?\s*((?-i:TBC)|(?-i:TBA)|to be confirmed)", text)
        if match is not None:
            ind = text.find(match[0])
            return ('date', ind, ind + len(match[0]), None, None, None, None, 'To Be Confirmed'), None
        else:
            return None, None


def extract_truckout_datetime(doc, get_whatever_date_found=False):
    text = doc.ori_text
    candidates = list()

    sent_begin_indices = list()
    last_sent_end_ind = 0
    for sent in sent_tokenize(text):
        ind = text.find(sent, last_sent_end_ind)
        sent_begin_indices.append(ind)
        last_sent_end_ind = ind + len(sent)
    sent_begin_indices = np.array(sent_begin_indices)

    all_datetimes = nlp.search_all_datetimes(text)
    for tup in all_datetimes:
        tup_begin_ind = tup[1]
        sent_begin_ind = sent_begin_indices[sent_begin_indices <= tup_begin_ind][-1]
        chars_before = text[max(sent_begin_ind, tup_begin_ind - 100):tup_begin_ind]

        chars_before = chars_before.lower()
        for keyword in ["truck-out", "truck out", "trucking out", "return"]:
            anchor_ind = chars_before.rfind(keyword)
            if anchor_ind >= 0:
                break

        if anchor_ind >= 0:
            candidates.append(tup)

    if get_whatever_date_found and (len(candidates) == 0) and (len(all_datetimes) > 0):
        candidates = all_datetimes[:2]
    # if get_whatever_date_found and (len(candidates) == 0):
    #     if (doc.lower_text.find("asap") < 30) or (doc.lower_text.find("now") < 30) or (doc.lower_text.find("immediately") < 30):
    #         return ('date', 0, 0, None, None, None, None, 'today'), ('time', 0, 0, None, None, None, None, 'now')

    candidates = [c for c in candidates if (c[4] != "not") and (c[4] != "n't")]

    if len(candidates) > 0:
        return process_datetime_candidates(candidates, text)
    else:
        match = re.search(
            "(?i)(" + "|".join(truckout_date_labels) + ")(?:\s+(?:date|time))?\s*(?:\:|is)?\s*((?-i:TBC)|(?-i:TBA)|to be confirmed)",
            text)
        if match is not None:
            ind = text.find(match[0])
            return ('date', ind, ind + len(match[0]), None, None, None, None, 'To Be Confirmed'), None
        else:
            return None, None


def extract_addresses(doc):
    text = doc.replaced_text

    with open("models/addr_NER_vocab_25009.pickle", "rb") as f:
        addr_ner_vocab = pickle.load(f)

    addr_NER = NerClassifier(25009, 50, 30, 13, 10, 6, 10, 5, bidirectionary_gru=True).to(device)
    addr_NER.load_state_dict(torch.load('models/addr_NER_V25009_E50_H30_10_6_L10_B_checkpoint_8.pt', map_location=torch.device('cpu')))
    addr_NER.eval()

    dataset = EntityDataset([text], target_entity_name=None, use_vocab=addr_ner_vocab)

    item = dataset[0]
    ori_text = dataset.ori_texts[0]
    tokens = np.array(dataset.tokenized_docs[0])
    x = item['x'].unsqueeze(0).to(device)
    x_crafted = item['x_crafted'].unsqueeze(0).to(device)

    with torch.no_grad():
        logprobs = addr_NER(x, x_crafted, dropout=True)
        _, predictions = torch.max(logprobs, 2)
        predictions = np.array(predictions[0].tolist()[1:len(tokens) + 1], dtype=int) - 1

        fragments_with_special_token = span_predictions_to_fragments(predictions, tokens, ori_text)
        fragments = list(fragments_with_special_token)

        for f, frag in enumerate(fragments_with_special_token):
            embedded_special_tokens = np.array(re.findall("_[A-Z]+(?:_[A-Z]+)?_", frag))
            for special_token in embedded_special_tokens:
                ever_replaced = [log[1] for log in doc.replacement_log if log[0] == special_token]
                if len(ever_replaced) == 1:
                    fragments[f] = fragments[f].replace(special_token, ever_replaced[0])
                elif len(ever_replaced) == np.sum(embedded_special_tokens == special_token):
                    search_from = 0
                    k = 0
                    string = ""
                    while True:
                        replace_at = frag.find(special_token, search_from)
                        if replace_at == 0:
                            string = ever_replaced[k]
                            k += 1
                            search_from = len(special_token)
                        elif replace_at > 0:
                            string += frag[search_from:replace_at] + ever_replaced[k]
                            k += 1
                            search_from = replace_at + len(special_token)
                        else:
                            string += frag[search_from:]
                            break
                    fragments[f] = string
                else:
                    restore_candidates = [fragments[f].replace(special_token, rep) for rep in ever_replaced]
                    fragments[f] = restore_candidates[0]

        if len(fragments) > 0:
            return fragments
        else:
            match = re.search(
                "(?i)(" + "|".join(delivery_addr_labels) + ")\s*(?:\:|is)?\s*((?-i:TBC)|(?-i:TBA)|to be confirmed)",
                doc.ori_text)
            if match is not None:
                return ["TBC"]
            else:
                return []


def extract_company(doc):
    text = doc.replaced_text

    spacy_comp_ner = spacy.load("models/comp_ner.spacy")
    results = [e.text for e in spacy_comp_ner(text).ents]
    if len(results) > 0:
        return results[0]

    with open("models/comp_NER_vocab_25401.pickle", "rb") as f:
        company_ner_vocab = pickle.load(f)

    company_NER = NerClassifier(25401, 50, 30, 13, 10, 6, 10, 5, gru_on_crafted_inputs=False, bidirectionary_gru=True).to(device)
    company_NER.load_state_dict(torch.load('models/comp_NER_V25401_E50_H30_10_6_L10_B_checkpoint_7.pt', map_location=torch.device('cpu')))
    company_NER.eval()

    dataset = EntityDataset([text], target_entity_name=None, use_vocab=company_ner_vocab)

    item = dataset[0]
    ori_text = dataset.ori_texts[0]
    tokens = np.array(dataset.tokenized_docs[0])
    x = item['x'].unsqueeze(0).to(device)
    x_crafted = item['x_crafted'].unsqueeze(0).to(device)

    with torch.no_grad():
        logprobs = company_NER(x, x_crafted, dropout=True)
        _, predictions = torch.max(logprobs, 2)
        predictions = np.array(predictions[0].tolist()[1:len(tokens) + 1], dtype=int) - 1

        fragments_with_special_token = span_predictions_to_fragments(predictions, tokens, ori_text)

        if len(fragments_with_special_token) > 0:
            return fragments_with_special_token[0]

    return None


def extract_container_numbers(doc):
    container_numbers = re.findall(container_no_regex, doc.ori_text)
    if len(container_numbers) > 0:
        return container_numbers
    else:
        match = re.search(
            "(?i)(?:" + "|".join(container_no_labels) + ")\s*(?:\:|is)?\s*((?-i:To Be Confirmed)|(?-i:TBA)|to be confirmed)",
            doc.ori_text)
        if match is not None:
            return ["To Be Confirmed"]
        else:
            return []


def extract_job_codes(doc):
    return re.findall(job_code_regex, doc.ori_text)


def extract_info(doc, expecting_slots=[]):
    has_update_later_intent = False

    vsl, voy = extract_vessel_voyage(doc)
    doc.data["vessel"] = vsl
    doc.data["voyage"] = voy
    eta_date, eta_time = extract_eta_datetime(doc)
    doc.data["eta_date"] = eta_date
    doc.data["eta_time"] = eta_time
    in_date, in_time = extract_truckin_datetime(doc)
    doc.data["in_date"] = in_date
    doc.data["in_time"] = in_time
    out_date, out_time = extract_truckout_datetime(doc)
    doc.data["out_date"] = out_date
    doc.data["out_time"] = out_time
    qty, foot_size, container_type = extract_qty_spe(doc)
    doc.data["qty"] = qty
    doc.data["foot_size"] = foot_size
    doc.data["cntr_type"] = container_type
    addr = extract_addresses(doc)
    doc.data["addr"] = addr
    comp = extract_company(doc)
    doc.data["comp"] = comp
    cntr_nums = extract_container_numbers(doc)
    doc.data["cntr_nums"] = cntr_nums
    job_codes = extract_job_codes(doc)
    doc.data["job_codes"] = job_codes

    if (((doc.lower_text.find("update") > 0) or (doc.lower_text.find("notify") > 0) or (doc.lower_text.find("inform") > 0) or (
            doc.lower_text.find("know") > 0)) and ((re.search(
        "(?i)(once|after|aft|when|becomes|become|upon)( \w+)*( is| it's)?\s*(available|have|gotten|got|ready|confirmed|approved|received|rcv)",
        doc.ori_text) is not None) or (re.search("(?i)(soon|asap|immediately|by today|by tomorrow|tomorrow|later|again)",
                                                 doc.ori_text) is not None))) or ((doc.lower_text.find("n't know") > 0) or (doc.lower_text.find("not know") > 0) or (doc.lower_text.find("not sure") > 0) or (doc.lower_text.find("not certain") > 0)):

        if (doc.data["eta_date"] is None) and (re.search("(?i)(" + "|".join(eta_date_labels) + ")", doc.ori_text) is not None):
            has_update_later_intent = True
            doc.data["eta_date"] = "To Be Confirmed"
        if (doc.data["in_date"] is None) and (re.search("(?i)(" + "|".join(truckin_date_labels) + ")", doc.ori_text) is not None):
            has_update_later_intent = True
            doc.data["in_date"] = "To Be Confirmed"
        if (doc.data["out_date"] is None) and (re.search("(?i)(" + "|".join(truckout_date_labels) + ")", doc.ori_text) is not None):
            has_update_later_intent = True
            doc.data["out_date"] = "To Be Confirmed"
        if (len(doc.data["addr"]) == 0) and (re.search("(?i)(" + "|".join(delivery_addr_labels) + ")", doc.ori_text) is not None):
            has_update_later_intent = True
            doc.data["addr"] = ["To Be Confirmed"]
        if (len(doc.data["cntr_nums"]) == 0) and (re.search("(?i)(" + "|".join(container_no_labels) + ")", doc.ori_text) is not None):
            has_update_later_intent = True
            doc.data["cntr_nums"] = ["To Be Confirmed"]
        if len(expecting_slots) > 0:
            for slot in expecting_slots:
                if doc.data.__contains__(slot):
                    if doc.data[slot] is None:
                        has_update_later_intent = True
                        doc.data[slot] = "To Be Confirmed"
                    elif (type(doc.data[slot]) == list) and (len(doc.data[slot]) == 0):
                        has_update_later_intent = True
                        doc.data[slot] = ["To Be Confirmed"]

    if expecting_slots.__contains__("eta_date") and doc.data["eta_date"] is None:
        doc.data["eta_date"], doc.data["eta_time"] = extract_eta_datetime(doc, True)
    if expecting_slots.__contains__("in_date") and doc.data["in_date"] is None:
        doc.data["in_date"], doc.data["in_time"] = extract_truckin_datetime(doc, True)

    for slot in doc.data:
        if type(doc.data[slot]) == list:
            if len(doc.data[slot]) > 0:
                return True, has_update_later_intent
        elif doc.data[slot] is not None:
            return True, has_update_later_intent
    return False, has_update_later_intent


def detect_simple_input_intent(doc, has_info_extracted=None):
    if re.search("^({})".format("|".join(["can", "could", "will", "would", "what", "where", "when", "which", "why", "is", "are", "do"])), doc.lower_text) is None:
        if has_info_extracted is None:
            has_info_extracted = extract_info(doc)
        date_val = nlp.search_date_pattern(doc.ori_text)
        num_match = re.search("(?:^|.*)(\d{1,3}|one|two|three|four|ten)(?:.*|$)", doc.lower_text)
        cntr_match = re.search(container_no_regex, doc.ori_text)
        job_code_match = re.search(job_code_regex, doc.ori_text)

        if has_info_extracted or (date_val is not None) or (num_match is not None) or (cntr_match is not None) or (job_code_match is not None):
            spacy_std = spacy.load("en_core_web_sm")
            tokens = list(spacy_std(doc.lower_text))
            for token in tokens:
                if (token.pos_ == "VERB") and (not ["can", "could", "will", "would"].__contains__(token.text)):
                    return 0
                elif token.pos_ == "PART":
                    return 0
            return 2
        else:
            return 0
    else:
        return 0


def detect_confirm_intent(doc, ctx=None):
    if (ctx is None) or (ctx.confirm_what != ""):
        text = " ".join(word_tokenize(doc.lower_text)[:10])
        if re.search("(?i)(?:^|[\s\.,\!])({})(?:$|[\s\.,\!])".format("|".join(["ok", "yes", "yap", "ya", "confirm", "agree", "alright", "right", "correct", "perfect", "sure", "great", "fantastic", "wonderful", "beautiful", "nice", "fine", "good", "cool", "proceed", "go ahead", "carry on", "no prob", "no issue", "not bad", "np", "definitely", "certainly"])),
                  text) is not None:
            spacy_std = spacy.load("en_core_web_sm")
            for token in spacy_std(doc.lower_text):
                if token.pos_ == "PART":
                    return 0
            return 2
    return 0


def detect_greeting_intent(doc):
    if is_greeting_statement(doc.ori_text, doc.lower_text, None):
        return 2
    else:
        return 0


def detect_decline_intent(doc):
    text = " ".join(word_tokenize(doc.lower_text)[:10])
    regex = "(?i)(?:.+)?(?:.+)?({})(?:$|[\s\.,\!])".format("|".join(["nop", "do not", "don't", "did not", "didn't", "not", "no", "wrong", "incorrect", "isn't right", "isn't correct", "not right", "not correct", "wait", "hang on", "hold on"]))
    return 2 * int((re.search(regex, text) is not None) & (text.find("no prob") == -1) & (text.find("no issue") == -1) & (text.find("not bad") == -1))


# doc = Document("i need a 20 footer tomorrow by 3pm. the vessel name is Titanic and the voy no. is V3422. the ETA is estimated to be on next friday but change to sat 7:59. please deliver to Lilok Pte Ltd, 29 Heng- Mui Keng Terrace, #02-22\n#03-48 Block D & E, Singapore 119620 without any delay.\n\nPlease also note that the container shall be picked up from at Eng Kong 11.")
# doc = Document("Truck in :  01 Jan 2020 (WED)\nTruck out: 31 Jan 2020 (THURS)\nPls park at\nAdvanced Regional Centre\nTampines LogisPark\n1 Greenwich Drive\nARC Warehouse Block 1, Level 2\nBay 1 to 9.")
# doc = Document("Please arrange to truck out the empty container accordingly as below without further delay.\nFrom TLH\n1.) FCIU2498150\nAddress:\n60 Tuas Bay Drive, S235323")
# doc = Document("i have an export here. the vsl will arrive on Tuesday at PSA port. The container number of FCIU2498150. please deliver it to Atos\n\nDelivery address: 10 Buroh Street, #03-15.")
# doc = Document("Kindly note the empty had reduce to 6 x 40 HC as below and please find revised Cartage advised")
# doc = Document("Vsl was delayed to 01/01/2020, as such delivery will be 02/01/2020")
# doc = Document("\n".join(["Tuesday", "Tuesday please", "on Tuesday", "truck in on Tuesday", "container number FCIU2498150", "ETA will be 23/02/2000", "delivery address: 10 Buroh Street, #03-15.", "1 x 20'GP", "1", "20 foot", "20GP", "postal code 640639", "Singapore 234344", "Atos"]))
# a, b = predict_book_intent(doc, include_stacked=True)
# b
# c, d = predict_update_intent(doc, include_stacked=True)
# d
# print(predict_book_intent(doc, include_stacked=True))
# print(predict_update_intent(doc, include_stacked=True))
#
# extract_vessel_voyage(doc)
# extract_eta_datetime(doc)
# extract_truckin_datetime(doc)
# extract_truckout_datetime(doc)
# extract_qty_spe(doc)
# extract_addresses(doc)
# extract_company(doc)
# predict_simple_input_intent(Document("ETA will be 23/02/2020"))
#
# # "yes", "no", "i don't agree", "Tuesday", "Tuesday please", "on Tuesday", "truck in on Tuesday", "container number FCIU2498150", "ETA will be 23/02/2020", "delivery address: 10 Buroh Street, #03-15.", "1 x 20'GP", "1", "20 foot", "20GP", "postal code 640639", "Singapore 234344", "Atos"
# for txt in ["i have an export. the vessel will arrive on Tuesday at PSA port. The container number of FCIU2498150. please deliver it to Atos\n\nDelivery address: 10 Buroh Street, #03-15.", "Kindly note the empty had reduce to 6 x 40 HC as below and please find revised Cartage advised", "Vsl was delayed to 01/01/2020, as such delivery will be 02/01/2020"]:
#     doc = Document(txt)
#     print(txt)
#     print([
#         predict_simple_input_intent(doc),
#         predict_book_intent(doc),
#         predict_update_intent(doc),
#         predict_confirm_intent(doc),
#         predict_decline_intent(doc)
#     ])