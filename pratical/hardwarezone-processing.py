import numpy as np
import pandas as pd
from datetime import datetime
import re
import spacy
from spacy.util import minibatch, compounding
import random

from lmpylib.core import *


nlp = spacy.load('en_core_web_lg')


def map_label(text):
    if pd.isna(text):
        return None
    elif text == "A":
        return 0
    elif text == "P":
        return 1
    elif text == "N":
        return -1
    elif text == "X":
        return -99


def remove_lf(text):
    if text.find("\n") > 0:
        return text.replace("\n", " ")
    else:
        return text


cent_data = pd.read_csv("data/hardwarezone-cents-new.csv", encoding="utf-8")
label_data = pd.read_csv("data/hardwarezone-cents-labels-0713.csv", encoding="utf-8")
label_data.columns = ["prod", "post", "performance", "keyboard", "screen", "portability", "battery", "price", "overall", "sent", "n_sent", "ori_sent_sn"]

all_data = pd.concat([cent_data, label_data.iloc[:, 2:9]], axis=1).fillna("")
all_data["sent"] = list(map(remove_lf, all_data["sent"]))
with_annotations = all_data.loc[(all_data["overall"] != "X") & ((all_data["performance"] != "") | (all_data["keyboard"] != "") | (all_data["screen"] != "") | (all_data["portability"] != "") | (all_data["battery"] != "") | (all_data["price"] != "") | (all_data["overall"] != "")), :].copy()
with_sentiments = with_annotations.loc[with_annotations["overall"] != "A", :]


def lower_case(string):
    return string.lower()


brand_series_data = pd.read_csv("data/laptop_brands_series.csv")
branded_series_data = brand_series_data.loc[brand_series_data["Brand"] != "ANY", :]
brand_set = set(map(lower_case, branded_series_data["Brand"].unique()))
series_set = set(map(lower_case, brand_series_data["Series"].unique()))


def append_text(text, append_text):
    if text == "":
        return append_text
    elif (append_text == ".") or (append_text == ",") or (append_text == "!") or (append_text == "?"):
        return text + append_text
    else:
        return text + " " + append_text


def make_new_text(doc, ent_placeholders, n_choice=None):
    all_training_data = list()
    if n_choice is None:
        n_choice = int(0.8*len(brand_series_data))
    for _ in range(n_choice):
        # np.random.choice(list(range(len(brand_series_data))), , replace=False):
        new_text = ""
        from_token = 0
        annotations = list()
        for ph in ent_placeholders:
            if type(ph) == tuple:
                cb = np.random.randint(0, len(branded_series_data), 1, dtype=int)[0]
                brand = branded_series_data.iat[cb, 0]
                series = branded_series_data.iat[cb, 1]

                org_ent = ph[0]
                prod_ent = ph[1]

                ent_text = brand
                if org_ent.lemma_.find("the ") == 0:
                    new_text = append_text(new_text, doc[from_token:(org_ent.start + 1)].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), "ORG"))
                    new_text = append_text(new_text, ent_text)
                elif org_ent.lemma_.find("a ") == 0:
                    new_text = append_text(new_text, doc[from_token:(org_ent.start + 1)].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), "ORG"))
                    new_text = append_text(new_text, ent_text)
                elif org_ent.start > from_token:
                    new_text = append_text(new_text, doc[from_token:org_ent.start].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), "ORG"))
                    new_text = append_text(new_text, ent_text)
                else:
                    if new_text == "":
                        annotations.append((0, len(ent_text), "ORG"))
                    else:
                        annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), "ORG"))
                    new_text = append_text(new_text, ent_text)

                ent_text = series
                annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), "PRODUCT"))
                new_text = append_text(new_text, ent_text)
            else:
                prod_ent = ph
                if brand_set.__contains__(prod_ent.lower_):
                    label = "ORG"
                    cb = np.random.randint(0, len(branded_series_data), 1, dtype=int)[0]
                    ent_text = branded_series_data.iat[cb, 0]
                else:
                    label = "PRODUCT"
                    cb = np.random.randint(0, len(brand_series_data), 1, dtype=int)[0]
                    ent_text = brand_series_data.iat[cb, 1]

                if prod_ent.lemma_.find("the ") == 0:
                    new_text = append_text(new_text, doc[from_token:(prod_ent.start + 1)].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), label))
                    new_text = append_text(new_text, ent_text)
                elif prod_ent.lemma_.find("a ") == 0:
                    new_text = append_text(new_text, doc[from_token:(prod_ent.start + 1)].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), label))
                    new_text = append_text(new_text, ent_text)
                elif prod_ent.start > from_token:
                    new_text = append_text(new_text, doc[from_token:prod_ent.start].text)
                    annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), label))
                    new_text = append_text(new_text, ent_text)
                else:
                    if new_text == "":
                        annotations.append((0, len(ent_text), label))
                    else:
                        annotations.append((len(new_text) + 1, len(new_text) + 1 + len(ent_text), label))
                    new_text = append_text(new_text, ent_text)

            from_token = prod_ent.end

        if from_token < len(doc):
            new_text = append_text(new_text, doc[from_token:].text)

        all_training_data.append((new_text, {
            "entities": annotations
        }))
    return all_training_data


all_new_annotated_text = list()
sent_texts = all_data["sent"].values
for i in range(len(sent_texts)):
    if i % 1000 == 0:
        print(i)

    doc_text = sent_texts[i]
    doc = nlp(doc_text)
    if len(doc) < 5:
        continue
    ents = list(doc.ents)
    ent_labels = np.array([w.label_ for w in ents])
    prod_org_ind = np.argwhere((ent_labels == "PRODUCT") | (ent_labels == "ORG")).flatten()
    if len(prod_org_ind) > 0:
        # print(len(all_new_annotated_text), i, doc_text)
        # print(ent_labels)
        # print([w for w in ents])

        if len(prod_org_ind) == 1:
            ent = ents[prod_org_ind[0]]
            new_annotated_text = make_new_text(doc, [ent])
            all_new_annotated_text.extend(new_annotated_text)
            # print(new_annotated_text, "\n")
        else:
            ent_placeholders = list()
            k = 1
            while k < len(prod_org_ind):
                ent_prev = ents[prod_org_ind[k - 1]]
                ent = ents[prod_org_ind[k]]
                if ent_prev.end == ent.start:
                    ent_placeholders.append((ent_prev, ent))
                    k += 1
                else:
                    ent_placeholders.append(ent_prev)
                    if k == len(prod_org_ind) - 1:
                        ent_placeholders.append(ent)
                k += 1

            if len(ent_placeholders) > 0:
                new_annotated_text = make_new_text(doc, ent_placeholders)
                all_new_annotated_text.extend(new_annotated_text)
                # print(new_annotated_text, "\n")

len(all_new_annotated_text)

all_new_annotated_text[31943]

print(nlp.pipe_names)

ner = nlp.get_pipe('ner')
optimizer = nlp.entity.create_optimizer()

n_iter = 10
other_pipes = [pipe for pipe in nlp.pipe_names if pipe != 'ner']
with nlp.disable_pipes(*other_pipes):  # only train NER
    for itn in range(n_iter):
        random.shuffle(all_new_annotated_text)
        losses = {}
        batches = minibatch(all_new_annotated_text, size=compounding(4., 32., 1.001))
        for batch in batches:
            texts, annotations = zip(*batch)
            # Updating the weights
            nlp.update(texts, annotations, sgd=optimizer, drop=0.35, losses=losses)
        print('Losses', losses)
        nlp.update(texts, annotations, sgd=optimizer, drop=0.35, losses=losses)
        print('Losses', losses)

doc = nlp("I think the ideapad is really duarable")
sent = list(doc.sents)[0]
print([w.label_ for w in doc.ents])
print([w for w in doc.ents])


k = 1
while k < 10:
    print(k)
    k += 1
    if k == 5:
        k += 1
for k in range(0, 10):
    print(k)
    if k == 5:
        k += 1


# cent_data_new = cent_data.loc[[False]*len(cent_data), :].copy()
# label_data["n_sent"] = 1
# label_data["ori_sent_sn"] = list(range(len(label_data)))
# label_data_new = label_data.loc[[False]*len(label_data), :].copy()
# for i, old_text in enumerate(all_data["sent"]):
#     if i % 1000 == 0:
#         print(i)
#     if old_text.find("\n") > 0:
#         new_text = remove_lf(old_text)
#         doc = nlp(new_text)
#         new_sents = list(doc.sents)
#         n_sent = len(new_sents)
#         if n_sent > 1:
#             for s, sent in enumerate(new_sents):
#                 row = cent_data.iloc[i, :]
#                 row["sent"] = sent.text.strip()
#                 cent_data_new = cent_data_new.append(row, ignore_index=True)
#
#                 row = label_data.iloc[i, :]
#                 row["sent"] = sent.text.strip()
#                 row["n_sent"] = n_sent
#                 label_data_new = label_data_new.append(row, ignore_index=True)
#         else:
#             cent_data_new = cent_data_new.append(cent_data.iloc[i, :], ignore_index=True)
#             label_data_new = label_data_new.append(label_data.iloc[i, :], ignore_index=True)
#     else:
#         cent_data_new = cent_data_new.append(cent_data.iloc[i, :], ignore_index=True)
#         label_data_new = label_data_new.append(label_data.iloc[i, :], ignore_index=True)
#
# cent_data_new.to_csv("data/hardwarezone-cents-new.csv", encoding="utf-8", index=False)
# label_data_new.to_csv("data/hardwarezone-labels-new.csv", encoding="utf-8", index=False)

