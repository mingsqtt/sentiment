import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import re
import pickle
from lmpylib.nlp import md5, search_all_datetimes


camelized_var = list()
for name in pd.read_csv("data/company-name-camelized.csv")["company"]:
    match = re.search("[a-z]", name)
    if match is not None:
        camelized_var.append(name)
hcp_companies = pd.read_csv("data/hcp_companies.csv")
all_companies = np.array(camelized_var + hcp_companies["company"].tolist())
all_addresses = pd.read_csv("data/companies.csv")["addr"]


def get_company_name_variations(com_name):
    without_suffix = com_name.replace(" & ", "&").replace(" And ", "&")
    without_suffix_cap = com_name.upper().replace(" & ", "&")
    abbr = None

    for suffix in ["Trading", "Finance", "Construction", "Singapore", "International", "South East Asia", "Asia", "ASIA", "(S) Pte Ltd", " S Pte Ltd", "(Singapore) Pte Ltd", "Singapore Pte Ltd", "(Singapore) Pte. Ltd.", "(SG) Pte Ltd", "SG Pte Ltd", "Co Pte Ltd", "Co (Pte) Ltd", "(Pte) Ltd", "Pte Ltd", "Pte. Ltd.", "PTE LTD", "PTE. LTD.", "Group", "Pte Limited", "Limited", "Enterprise", "Holdings", "Corp", "& Co", "Co", "COM", "Ltd", "LTD", "Llp", "LLP", "Llc", "LLC", " S"]:
        idx = com_name.rfind(suffix)
        if (idx > 0) and (idx == (len(com_name) - len(suffix))):
            without_suffix = com_name[:idx].strip().replace(" & ", "&")
            without_suffix_cap = without_suffix.upper()
            break

    parts = without_suffix.split(" ")
    if len(parts) > 1:
        part0 = parts[0]
        match = re.search("^[a-z]?[A-Z&]{2,7}$", part0)
        if match is not None:
            abbr = part0
        else:
            match = re.search("^([A-Z])\w+\s([A-Z])\w+\s([A-Z])\w+", without_suffix)
            if match is not None:
                abbr = match[1] + match[2] + match[3]

    return abbr, without_suffix, without_suffix_cap


abbr_list, without_suffix_list, without_suffix_cap_list, name_cap_list = list(), list(), list(), list()
for name in all_companies:
    abbr, without_suffix, without_suffix_cap = get_company_name_variations(name)
    abbr_list.append(abbr)
    without_suffix_list.append(without_suffix)
    without_suffix_cap_list.append(without_suffix_cap)
    name_cap_list.append(name.upper())
all_companies_vars = pd.DataFrame({
    "name": all_companies,
    "abbr": abbr_list,
    "without_suffix": without_suffix_list,
    "without_suffix_cap": without_suffix_cap_list,
    "name_cap": name_cap_list
})
unique_abbr_list = list(set([a for a in abbr_list if a is not None]))

addr_comp_preceding = "(?:^|(?<=[\s\.,:<>]))"
road_synonyms = "road|rd|street|st|avenue|ave|drive|dr|central|ctrl|north|south|east|west|close|cresent|cres|place|terrace|circle|highway|way|view|boulevard|blvd|lane|link|quay|square|loop|sector|walk|farmway|Penjuru|Ampat|estate|promenade|heights|height|plaza|green|junction|grove|bahru|rise|grande|toa\spayoh|hill|turn|garden|gate"
park_synonyms = "industry\spark|industrial\spark|industrial\sestate|business\spark|biz\spark|tech\spark|agrotechnology\spark"
postal_regex = "(?i)" + addr_comp_preceding + "((?:Singapore|SG|S)\s*[\(\-]?[0-9]{6}\)?)(?![0-9a-zA-Z\-/_])"
block_part = "\d+[A-Z]?(?:[/\-](?:[A-Z]|\d+[A-Z]?)){0,2}"
block_street_regex1 = "(?i)" + addr_comp_preceding + "(" + block_part + ")[\s,].+\s(" + road_synonyms + ")(?:\s(?:\d{1,2}|I|II|III))?"
block_street_regex2 = "(?i)" + addr_comp_preceding + "(" + block_part + ")[\s,](?:jalan|jln|lorong|lor|mount|pulau)\s.+"
block_street_regex3 = "(?i)" + addr_comp_preceding + "(" + block_part + ")[\s,].+\s(?:" + park_synonyms + ")(?:\s(?:\d{1,2}|I|II|III))?"
core_unit_part = "B?\d+[A-Z]?\d?(?:[\-/]B?\d*[A-Z]?\d?){0,9}"
unit_part_regex = "(?:unit\s|suite\s|#)" + core_unit_part + "(?:\s?/\s?#" + core_unit_part + "){0,5}"
unit_building_regex = "(?i)" + addr_comp_preceding + "(" + unit_part_regex + ")(?:([\s,].*)|$)"
level_building_regex = "(?i)" + addr_comp_preceding + "((?:\d+(?:st|nd|rd|th)\s+)?(?:level|story|storey|floor|lv|basement)(?:\s+B?\d+[A-Za-z]?)?)(?:([\s,].*)|$)"
mailbox_building_regex = "(?i)" + addr_comp_preceding + "(?:mail\sbox|mailbox|box)\s+\d+(?:([\s,].+)|$)"


address_lines, address_line_tags, number_parts = list(), list(), list()
place_lines, block_street_lines, building_lines = set(), set(), set()
for i, addr_lines in enumerate(all_addresses):
    for line in addr_lines.split("\n"):
        num_part = None
        match_postal = re.search(postal_regex, line)
        if match_postal is None:
            match_blk_street1 = re.search(block_street_regex1, line)
            if match_blk_street1 is None:
                match_blk_street2 = re.search(block_street_regex2, line)
                if match_blk_street2 is None:
                    match_blk_street3 = re.search(block_street_regex3, line)
                    if match_blk_street3 is None:
                        match_unit_building = re.search(unit_building_regex, line)
                        if match_unit_building is None:
                            match_level_building = re.search(level_building_regex, line)
                            if match_level_building is None:
                                match_mailbox_building = re.search(mailbox_building_regex, line)
                                if match_mailbox_building is None:
                                    address_line_tags.append("place")
                                    place_lines.add(line)
                                else:
                                    address_line_tags.append("box_building")
                            else:
                                address_line_tags.append("level_building")
                                num_part = match_level_building[1]
                                building_lines.add(line.replace(match_level_building[1], "").strip())
                        else:
                            address_line_tags.append("unit_building")
                            num_part = match_unit_building[1]
                            building_lines.add(line.replace(match_unit_building[1], "").strip())
                    else:
                        address_line_tags.append("block_street")
                        num_part = match_blk_street3[1]
                        block_street_lines.add(line)
                else:
                    address_line_tags.append("block_street")
                    num_part = match_blk_street2[1]
                    block_street_lines.add(line)
            else:
                address_line_tags.append("block_street")
                num_part = match_blk_street1[1]
                block_street_lines.add(line)
                block_street_lines.add(line.replace("Road", "Rd").replace("Street", "St").replace("Avenue", "Ave").replace("Drive", "Dr").replace("Cresent", "Cres").replace("Boulevard", "Blvd").replace("Sector", "Sec"))
        else:
            address_line_tags.append("postal")
        address_lines.append(line)
        number_parts.append(num_part)
place_lines = list(place_lines)
block_street_lines = list(block_street_lines)
building_lines = list(building_lines)


def fill_prob(entries):
    residual = 1.0
    none_indices = list()
    cats1, cats2, probs = [None]*len(entries), [None]*len(entries), [None]*len(entries)
    tup_size = len(entries[0])
    for i, entry in enumerate(entries):
        if tup_size == 2:
            cats1[i] = entry[0]
        elif tup_size == 3:
            cats1[i] = entry[0]
            cats2[i] = entry[1]

        p = entry[tup_size - 1]
        if p is None:
            none_indices.append(i)
        else:
            residual -= p
            if tup_size == 2:
                probs[i] = entry[1]
            elif tup_size == 3:
                probs[i] = entry[2]

    if len(none_indices) == 1:
        probs[none_indices[0]] = residual
    elif len(none_indices) > 1:
        each = np.floor(residual * 1e7 / len(none_indices)) / 1e7
        none0 = none_indices[0]
        probs[none0] = np.round(residual - each * (len(none_indices) - 1), 7)
        for i in range(1, len(none_indices)):
            none1 = none_indices[i]
            probs[none1] = each
    psum = np.round(np.sum(probs), 7)
    assert psum == 1.0, "probability is not 1.0, but got {}".format(psum)
    return cats1, cats2, probs


addr_templates, _, addr_template_prob = fill_prob([
    ("<place><separator><block_street><separator>_UNIT_LEVEL_ <building><opt_postal>", None),
    ("<place><separator><block_street><opt_postal>", 0.14),
    ("<building><separator><block_street><opt_postal>", 0.14),
    ("<place> <building><separator><block_street><opt_postal>", 0.14),
    ("<block_street><separator><place><opt_postal>", None),
    ("<block_street><separator><building><opt_postal>", None),
    ("<block_street><separator><place><separator>_UNIT_LEVEL_<opt_postal>", 0.07),
    ("<block_street><separator><building><separator>_UNIT_LEVEL_<opt_postal>", 0.07),
    ("<block_street>, _POSTAL_<separator><place>", 0.14),
    ("<block_street>, _POSTAL_<separator>_UNIT_LEVEL_ <building>", None),
    ("<block_street><opt_postal>", None),
])


def gen_addr(template=None, inline_only=True, include_annotation=True):
    capitalized = np.random.rand() > 0.95

    if template is None:
        template = np.random.choice(addr_templates, 1, p=addr_template_prob)[0]

    if inline_only:
        separator = np.random.choice([",", ", ", " "], 1, p=[0.05, 0.65, 0.3])[0]
    else:
        separator = np.random.choice([",", ", ", " ", "\n", ",\n"], 1, p=[0.05, 0.3, 0.15, 0.4, 0.1])[0]

    if np.random.rand() > 0.3:
        if inline_only:
            opt_postal = np.random.choice([",", ", ", " "], 1, p=[0.05, 0.75, 0.2])[0] + "_POSTAL_"
        else:
            opt_postal = separator + "_POSTAL_"
    else:
        opt_postal = ""
    block_street = block_street_lines[np.random.randint(0, len(block_street_lines), 1)[0]]
    place = place_lines[np.random.randint(0, len(place_lines), 1)[0]]
    building = building_lines[np.random.randint(0, len(building_lines), 1)[0]]
    if capitalized:
        block_street = block_street.upper()
        place = place.upper()
        building = building.upper()

    generated = template
    generated = generated.replace("<separator>", separator)
    generated = generated.replace("<opt_postal>", opt_postal)
    generated = generated.replace("<block_street>", block_street)
    generated = generated.replace("<place>", place)
    generated = generated.replace("<building>", building)

    if include_annotation:
        return "<addr>" + generated + "</addr>"
    else:
        return generated


def gen_company(include_annotation=True):
    col_indices = np.random.choice([0, 1, 2, 3, 4], 2, replace=False, p=[0.1, 0.5, 0.2, 0.1, 0.1])
    row_index = np.random.randint(0, len(all_companies_vars), 1)[0]
    var1, var2 = all_companies_vars.iloc[row_index, col_indices]

    if include_annotation:
        company = "<company>" + (var1 if var1 is not None else var2) + "</company>"
    else:
        company = var1 if var1 is not None else var2
    if np.random.rand() > 0.95:
        company += " Warehouse"
    return company


def gen_company_abbr():
    return unique_abbr_list[np.random.randint(0, len(unique_abbr_list), 1)[0]]


def gen_company_addr(inline_only=True, include_annotation=True):
    generated_addr = gen_addr(inline_only=inline_only, include_annotation=include_annotation)
    if np.random.rand() > 0.5:
        generated_comp = gen_company(include_annotation)

        if generated_addr.find("\n") > 0:
            separator = "\n"
        elif inline_only:
            separator = np.random.choice([",", ", ", " ", " - "], 1, p=[0.05, 0.6, 0.2, 0.15])[0]
        else:
            separator = np.random.choice([",", ", ", " ", " - ",  "\n", ",\n"], 1, p=[0.01, 0.29, 0.05, 0.4, 0.1])[0]

        if np.random.rand() > 0.9:
            return generated_comp + separator + generated_addr
        else:
            return generated_addr + separator + generated_comp
    else:
        return generated_addr


