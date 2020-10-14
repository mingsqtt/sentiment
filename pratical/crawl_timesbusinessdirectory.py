import re
import requests
import json
import math
import time
from bs4 import BeautifulSoup
from feedparser import parse
from datetime import datetime
import pandas as pd
import numpy as np
import spacy
from spacy import displacy


headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36"
}
params = {}
url_template = 'https://www.timesbusinessdirectory.com/company-listings?co={}&page={}'


def crawl(comp_df, co="A", from_page=1, to_page=1000):
    for page in range(max(from_page, 1), to_page + 1):
        page_url = url_template.format(co, page)
        comp_df, count = crawl_listing_page(page_url, comp_df)
        print(co, "Page", page, count)
        if count == 0:
            break
    return comp_df


def crawl_listing_page(page_url, comp_df):
    resp = requests.get(page_url, params=params, headers=headers)
    if resp.status_code == 200:
        content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
        soup = BeautifulSoup(content, 'html.parser')
        comp_div_tags = soup.find_all("div", {"class": "company-details"})
        for i, comp_tag in enumerate(comp_div_tags):
            a_tag = comp_tag.find("a")
            img_tag = a_tag.find("img")
            if img_tag is not None:
                comp_name = img_tag.attrs["title"]
            else:
                comp_name = a_tag.getText().strip()
            comp_addr = list()

            resp = requests.get("https://www.timesbusinessdirectory.com" + a_tag.attrs["href"], params=params, headers=headers)
            if resp.status_code == 200:
                content = re.sub(r'[\n\r()]', '', resp.content.decode(resp.encoding))
                soup = BeautifulSoup(content, 'html.parser')
                p_tag = soup.find("div", {"class": "company-contact"}).find("p")
                for child_tag in p_tag.children:
                    if (child_tag.name is None) and (child_tag.strip() != ""):
                        comp_addr.append(child_tag.strip())

            comp_df = comp_df.append({
                "name": comp_name,
                "addr": "\n".join(comp_addr)
            }, ignore_index=True)

        return comp_df, len(comp_div_tags)
    else:
        return comp_df, 0


df = pd.DataFrame({
    "name": [],
    "addr": []
})

for c in range(65, 65+26):
    df0 = crawl(df, co=str(chr(c)))
    df0.to_csv("data/companies-{}.csv".format(chr(c)), index=False)

df = pd.read_csv("data/companies.csv")


camelizable = {"OF", "IN", "ON", "AN", "CO", "AH", "AS", "DA", "OH", "PTE", "LTD", "LLP", "LLC", "TAN", "KOK", "HOH", "YEW", "YOE", "ONE", "ANG", "HUB", "SUN", "EGG", "JET", "PAN", "OAK", "ICE", "LAW", "AIR", "OIL", "GAS", "CAR", "BUS", "SEA", "ALL", "FAR", "BIG", "FOR", "SKY", "AND", "RED", "GEM", "CAP", "NAM", "AIK", "LEE", "MOH", "HIN", "BEN", "LAY", "HUI", "TAT", "GOH", "WOH", "BEE", "WEE", "HOE", "ENG", "YAM", "MAN", "KEE", "HUP", "HUA", "HUP", "LIM", "LIN", "ONG", "XIN", "DOW", "SIN", "TIE", "HWA", "LAM", "MOK", "JIA", "HOR", "WOO", "KAY", "FAT", "RAY", "HOW", "POE", "TAY", "HOY", "BAN", "BOK", "YUN", "YIK", "FOO", "BAY", "ANN", "JOO", "YIH", "MAI", "TAI", "SOH", "MEE", "PAK", "NET", "TEH", "LOW", "WEI", "SAM", "LAM", "BOX", "OLD", "ZEE", "YEE", "MAY", "DEE", "MUI", "HEN", "HAK", "KIM", "WAY", "JIN", "RAM", "NAI", "LAI", "WAI", "MEI", "HOO", "EAR", "TEO", "BAO", "WAN", "WEN", "SHI", "CHU", "SUM", "TAH", "TEA", "KOR", "HUR", "TIN", "NEO", "LEO", "LIH", "PEH", "GEE", "KUO", "YIN", "BON", "HOP", "SAY", "LOK", "PIN", "YAP", "OWL", "WOH", "NEW", "SOO", "EEK", "WIN", "KAO", "JAY", "TWO", "TEN", "DAY", "KUN", "FAN", "HAI", "HAN", "ART", "LEY", "BAR", "PAY", "EYE", "GAN", "DOU", "ONN", "LOO", "KIA", "JOE", "JAM", "KEN", "POH"}


def to_be_cap(text):
    if (len(text) == 2) or (len(text) == 3):
        if text.lower() == text:
            return False
        else:
            return not camelizable.__contains__(text)
    else:
        return False


def to_camel(text):
    n_text = len(text)
    if n_text == 1:
        return text
    elif n_text <= 3:
        if camelizable.__contains__(text):
            return text[:1] + text[1:].lower()
        else:
            return text
    else:
        return text[:1] + text[1:].lower()


def get_name_variations(name):
    variations = list()
    for v in range(2):
        parts = list()
        any_cap = False
        for part in name.split(" "):
            any_cap = any_cap | to_be_cap(part)
            if part.find("/") > 0:
                sub_parts = list()
                for part0 in part.split("/"):
                    any_cap = any_cap | to_be_cap(part0)
                    sub_parts.append(to_camel(part0))
                parts.append("/".join(sub_parts))
            elif part.find("-") > 0:
                sub_parts = list()
                for part0 in part.split("-"):
                    any_cap = any_cap | to_be_cap(part0)
                    sub_parts.append(to_camel(part0))
                parts.append("-".join(sub_parts))
            elif part.find(".") >= 0:
                any_cap = True
                parts.append(part)
            else:
                parts.append(to_camel(part))
        variations.append(" ".join(parts))
        if not any_cap:
            break

    if name.find(" PTE LTD") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" PTE LTD")])
    elif name.find(" PTE. LTD.") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" PTE. LTD.")])
    elif name.find(" LTD") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" LTD")])
    elif name.find(" LLP") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" LLP")])
    elif name.find(" LLC") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" LLC")])
    elif name.find(" GROUP") > 0:
        variations.append(variations[len(variations) - 1][:name.find(" GROUP")])

    if len(variations) == 1:
        return variations[0]
    else:
        return np.unique(np.array(variations)).tolist()


df.loc[df["name"] == "SAAA@SINGAPORE", "name"] = "SAAA @ SINGAPORE"

name_variations = list()
for n in df["name"]:
    var = get_name_variations(n)
    if type(var) == list:
        name_variations.extend(var)
    else:
        name_variations.append(var)
all_names_df = pd.DataFrame({"company": df["name"].tolist() + name_variations})
all_names_df.to_csv("data/company-name-camelized.csv", index=False)


def try_append_block_level(block_no, level_no, var_lines):
    parts = list()
    if block_no is not None:
        if np.random.choice([True, False], 1)[0]:
            parts.append("Block " + block_no)
        else:
            parts.append("Blk " + block_no)
    if level_no is not None:
        if np.random.choice([True, False], 1)[0]:
            parts.append("Level " + level_no)
        else:
            parts.append("Lvl " + level_no)
    if len(parts) > 0:
        var_lines.append(", ".join(parts))
    return None, None, var_lines


def try_append_bay(bay_from, bay_to, var_lines):
    parts = list()
    if bay_from is not None:
        parts.append("Bay " + bay_from)
    if bay_to is not None:
        if np.random.choice([True, False], 1)[0]:
            parts.append(" - " + bay_to)
        else:
            parts.append(" to " + bay_to)
    if len(parts) > 0:
        var_lines.append("".join(parts))
    return var_lines


def get_addr_variations(addr, separate="\n"):
    variations = list()
    lines = addr.split("\n")

    var_lines = list()
    postal_style = np.random.choice([0, 1, 2, 3], 1, p=[0.02, 0.7, 0.14, 0.14])[0]
    for line in lines:
        if line.find("Singapore ") == 0:
            if postal_style == 1:
                var_lines.append(line)
            elif postal_style == 2:
                var_lines.append("S(" + line[10:] + ")")
            elif postal_style == 3:
                var_lines.append("S (" + line[10:] + ")")
        else:
            var_lines.append(line)
    variations.append(separate.join(var_lines))

    var_lines = list()
    block_no = np.random.choice([None, "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F", "G", "H", "A1", "B2", "C3"], 1, p=[0.9] + [0.008]*10 + [0.002]*10)[0]
    level_no = np.random.choice([None, "1", "2", "3", "4", "5", "6", "7", "8"], 1, p=[0.6] + [0.05]*8)[0]
    bay_no1 = np.random.choice([None, "1", "2", "3", "4", "5", "6", "7", "8"], 1, p=[0.6] + [0.05]*8)[0]
    if bay_no1 is not None:
        bay_no2 = np.random.choice([None, "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20"], 1, p=[0.4] + [0.05] * 12)[0]
    else:
        bay_no2 = None
    postal_style = np.random.choice([0, 1, 2, 3], 1, p=[0.15, 0.5, 0.25, 0.10])[0]
    for line in lines:
        if line.find("Singapore ") == 0:
            if postal_style == 0:
                pass
            elif postal_style == 1:
                var_lines.append(line)
            elif postal_style == 2:
                var_lines.append("S(" + line[10:] + ")")
            elif postal_style == 3:
                var_lines.append("S (" + line[10:] + ")")
        elif line.find("#") >= 0:
            block_no, level_no, var_lines = try_append_block_level(block_no, level_no, var_lines)

            parts = list()
            for part in line.split(" "):
                if part.find("#") >= 0:
                    if np.random.choice([True, False], 1)[0]:
                        pass
                    else:
                        parts.append(part.replace("#", "Unit "))
                else:
                    parts.append(part)
            if len(parts) > 0:
                var_lines.append(" ".join(parts))

            block_no, level_no, var_lines = try_append_block_level(block_no, level_no, var_lines)
        else:
            var_lines.append(line)
    block_no, level_no, var_lines = try_append_block_level(block_no, level_no, var_lines)
    var_lines = try_append_bay(bay_no1, bay_no2, var_lines)
    variations.append(separate.join(var_lines))

    if (len(var_lines) > 2) and (len(lines) > 2):
        temp = var_lines[0]
        var_lines[0] = var_lines[1]
        var_lines[1] = temp
        variations.append(separate.join(var_lines))

    variations.append(separate.join(lines))

    if len(variations) == 1:
        return variations[0]
    else:
        return np.unique(np.array(variations)).tolist()


addr_variations = list()
for a in df["addr"]:
    if np.random.choice([True, False], 1)[0]:
        var = get_addr_variations(a, separate=", ")
    else:
        var = get_addr_variations(a, separate=" ")
    if type(var) == list:
        addr_variations.extend(var)
    else:
        addr_variations.append(var)
flatten_addr_df = pd.DataFrame({"addr": addr_variations})
flatten_addr_df.to_csv("data/company-addr-var-flatten.csv", index=False)


addr_variations = list()
for a in df["addr"]:
    var = get_addr_variations(a, separate="\n")
    if type(var) == list:
        addr_variations.extend(var)
    else:
        addr_variations.append(var)
all_addr_df = pd.DataFrame({"addr": addr_variations})
all_addr_df.to_csv("data/company-addr-var.csv", index=False)


augmented_names = list()
augmented_addr = list()
n_address = 10
for n in name_variations:
    augmented_names.extend([n] * n_address)
    augmented_addr.extend(np.random.choice(addr_variations, n_address, replace=False).tolist())
recombined_df = pd.DataFrame({"name": augmented_names, "addr": augmented_addr})
recombined_df.to_csv("data/company-augmented.csv", index=False)




