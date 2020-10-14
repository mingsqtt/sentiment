import numpy as np
import pandas as pd
from datetime import datetime
import re
import spacy
from spacy.util import minibatch, compounding
import random

from lmpylib.core import *
from lmpylib import nlp

# chat_data = pd.read_csv("data/CommunityProduction_dbo_ChatRecords.csv")
# chat_data.head(5)
# chat_data["time"] = pd.to_datetime(chat_data["time"])
# chat_data["from_haulio"] = chat_data["from_user"].str.find("@haulio.io") > 0
# # chat_data["with_com"] = (chat_data["from_com"].values - 56) + (chat_data["to_com"].values - 56) + 56
# chat_data["with_com"] = pd.Series(np.minimum(chat_data["from_com"].values, chat_data["to_com"].values).astype(str)) + "&" + pd.Series(np.maximum(chat_data["from_com"].values, chat_data["to_com"].values).astype(str))
# k = chat_data[["with_com", "id"]].groupby("with_com", as_index=False).count()
# high_freq_com = k.loc[(k["id"] >= 10), "with_com"].values
#
# chat_data = chat_data.sort_values(["with_com", "time"])
#
# prev_with = shift_down(chat_data["with_com"], fill_head_with=-999)
# next_with = shift_up(chat_data["with_com"], fill_tail_with=-999)
# prev_time = shift_down(chat_data["time"])
# com_start = chat_data["with_com"] != prev_with
# com_end = chat_data["with_com"] != next_with
# time_del = np.array((chat_data["time"].values - pd.to_datetime(pd.Series(prev_time)).values) / np.timedelta64(1, 'm'), dtype=int)
# time_del[com_start] = 0
# chat_data["time_del"] = time_del
#
#
# text_lower = chat_data["text"].str.lower()
# trainable_filt = chat_data["with_com"].isin(high_freq_com) & (chat_data["is_file"] == 0) & (text_lower.str.find("hello, thank you") != 0) & (text_lower.str.find("hi, thank you") != 0) & (text_lower.str.find("hi, thanks for your booking") != 0) & (text_lower.str.find("nice, job completed!") == -1) & (text_lower.str.find("the following submissions will not be accepted") != 0)
# with2_filt = chat_data["with_com"] == "2&56"
#
# summary(chat_data["with_com"], is_numeric=False)
# summary(trainable_filt)
# list(chat_data.loc[trainable_filt, "text"].values[10000:11000])
#
# chat_data.loc[trainable_filt & with2_filt, ["text"]]
# chat_data.loc[trainable_filt & (chat_data["from_haulio"] == False), ["time_del", "text", "from_user"]]







newest_bodies = lines_data[["doc_md5", "body_id"]].groupby("doc_md5", as_index=False).min()
newest_bodies_id = set(newest_bodies["body_id"].unique())
dialog_line_data = lines_data.loc[lines_data["body_id"].isin(newest_bodies_id), :]


doc_id = 0
trainable_body_ids = list()
trainable_doc_ids = list()
trainable_doc_text = list()
trainable_doc_senders = list()
trainable_doc_md5 = list()
for body_id in bodies:
    if newest_bodies_id.__contains__(body_id):
        doc_id += len(bodies[body_id])
        continue
    for doc in bodies[body_id]:
        sender = doc["sender"]
        doc_lines = doc["lines"]
        if len(doc_lines) > 0:
            doc_text = "\n".join(doc_lines)
            trainable_body_ids.append(body_id)
            trainable_doc_ids.append(doc_id)
            trainable_doc_text.append(doc_text)
            trainable_doc_senders.append(sender)
            trainable_doc_md5.append(nlp.md5(doc_text))
        doc_id += 1

trainable_doc_df = pd.DataFrame({
    "body_id": trainable_body_ids,
    "doc_id": trainable_doc_ids,
    "text": trainable_doc_text,
    "sender": trainable_doc_senders,
    "incoming": [s.find("@haulio.io") == -1 for s in trainable_doc_senders],
    "doc_md5": trainable_doc_md5
})
trainable_doc_df.to_csv("data/trainable_doc_df.csv", index=False, encoding="utf-16")
# trainable_dialogs = dialog_line_data.loc[dialog_line_data["incoming"] & (dialog_line_data["n_parts"] > 5), ["line_md5", "line"]].groupby("line_md5").first()


trainable_lines = lines_data.loc[(line_level_n_parts > 5) & lines_data["incoming"], ["body_id", "doc_id", "sender", "line", "line_md5", "doc_md5", "new_doc"]]
long_lines = lines_data.loc[(line_level_n_parts > 10) & lines_data["incoming"], ["body_id", "doc_id", "sender", "line", "line_md5", "doc_md5", "new_doc"]]
short_lines = lines_data.loc[(line_level_n_parts <= 5) & lines_data["incoming"], ["body_id", "doc_id", "sender", "line", "line_md5", "doc_md5", "new_doc"]]


unique_trainable = trainable_lines[["line_md5", "line"]].groupby("line_md5").first().sort_values("line")
unique_trainable["line_lower"] = unique_trainable["line"].str.lower()
pls_lines = unique_trainable.loc[(unique_trainable["line_lower"].str.find("please") >= 0) | (unique_trainable["line_lower"].str.find("kindly") >= 0), :]
arrange_lines = unique_trainable.loc[(unique_trainable["line_lower"].str.find("arrange") >= 0) | (unique_trainable["line_lower"].str.find("book") >= 0), :]
arrange_noatt_lines = unique_trainable.loc[(unique_trainable["line_lower"].str.find("arrange") >= 0) & (unique_trainable["line_lower"].str.find("attach") == -1), :]


unique_nosg_trainable = unique_trainable.loc[(unique_trainable["line_lower"].str.find("singapore") == -1) & (unique_trainable["line_lower"].str.find("location") == -1) & (unique_trainable["line_lower"].str.find("road") == -1) & (unique_trainable["line_lower"].str.find("street") == -1) & (unique_trainable["line_lower"].str.find("ave") == -1) & (unique_trainable["line_lower"].str.find("industr") == -1) & (unique_trainable["line_lower"].str.find("pte") == -1), :].copy()
unique_before = unique_nosg_trainable.loc[(unique_nosg_trainable["line_lower"].str.find("please") >= 0) | (unique_nosg_trainable["line_lower"].str.find("kindly") >= 0), :]
recombined_df = pd.read_csv("data/company-augmented.csv")
company_name_addr_training_data = list()
for r, row in recombined_df.iterrows():
    comp_name = row["name"]
    comp_addr = row["addr"]

    for n in range(3):
        lines = list()
        annotations = list()
        text_length = 0
        before_lines = unique_before.iloc[np.random.randint(0, len(unique_before), np.random.randint(1, 3, 1)[0]), 0].tolist()
        n_before_short = short_lines.iloc[np.random.randint(0, len(short_lines), np.random.randint(0, 4, 1)[0]), 3].tolist()
        n_after_long = unique_nosg_trainable.iloc[np.random.randint(0, len(unique_nosg_trainable), np.random.randint(0, 3, 1)[0]), 0].tolist()

        for ln in before_lines:
            lines.append(ln)
            text_length += len(ln) + 1

        for ln in n_before_short:
            lines.append(ln)
            text_length += len(ln) + 1

        if n == 0:
            annotations.append((text_length, text_length + len(comp_name), "COMPANY"))
            lines.append(comp_name)
            text_length += len(comp_name) + 1

        annotations.append((text_length, text_length + len(comp_addr), "ADDRESS"))
        lines.append(comp_addr)

        lines.extend(n_after_long)

        company_name_addr_training_data.append(("\n".join(lines), {
            "entities": annotations
        }))

    if r % 1000 == 0:
        print(r)




unique_trainable.loc["77344bad9e92c29d8bf7b6bdf07968ab", "line"]
lines_data.loc[lines_data["line_md5"] == "77344bad9e92c29d8bf7b6bdf07968ab", :]
lines_data.loc[lines_data["body_id"] == 27800, ["doc_id", "sender", "line", "doc_md5"]]
lines_data.loc[lines_data["body_id"] == 27798, ["doc_id", "sender", "line", "doc_md5"]]
lines_data.loc[lines_data["body_id"] == 27793, ["doc_id", "sender", "line", "doc_md5"]]
lines_data.loc[lines_data["body_id"] == 27666, ["doc_id", "sender", "line", "doc_md5"]]


txt = doc_df.loc[doc_df["body_id"] == 40053, "text"].values[0]
nlp_lg = spacy.load('en_core_web_lg')
spacy_doc = nlp_lg("Can you advised total is 112 x 40’RH or 114 x 40’RH trucked out for below job order? Possible to send me the container list for my checking?")
sents = list(spacy_doc.sents)
for s in sents:
    for c in s:
        print(c)


ner = nlp_lg.get_pipe('ner')
ner.add_label("COMPANY")
ner.add_label("ADDRESS")
optimizer = nlp_lg.entity.create_optimizer()

n_iter = 2
other_pipes = [pipe for pipe in nlp_lg.pipe_names if pipe != 'ner']
with nlp_lg.disable_pipes(*other_pipes):  # only train NER
    for itn in range(n_iter):
        random.shuffle(company_name_addr_training_data)
        losses = {}
        batches = minibatch(company_name_addr_training_data, size=compounding(4., 32., 1.001))
        for batch in batches:
            texts, annotations = zip(*batch)
            # Updating the weights
            nlp_lg.update(texts, annotations, sgd=optimizer, drop=0.35, losses=losses)
        print('Losses', losses)
        nlp_lg.update(texts, annotations, sgd=optimizer, drop=0.35, losses=losses)
        print('Losses', losses)






