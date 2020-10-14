import numpy as np
import pandas as pd
from datetime import datetime
import re
import spacy
from spacy.util import minibatch, compounding
import random
import pickle

from lmpylib.core import *
from lmpylib import nlp

with open("data/bodies.pickle", "rb") as f:
    bodies = pickle.load(f)

indentations = {}
intent_labels = "<intent>book book_att standby update update_later finalize other_order inquire info agree disagree end others</intent>"
sent_intent_labels = "<intent>book book_att standby update update_later finalize other_order inquire info agree disagree end others data notes</intent>"
job_type_labels = "<jt>import export oneway</jt>"


def get_indentation(n):
    if not indentations.__contains__(n):
        indentations[n] = "".join([" "] * n)
    return indentations[n]


def to_labelling_friendly(body_id, docs, docs_md5, docs_incoming, append_breaks=True):
    prt_lines = list()
    prt_lines.append("======================================================= BODY =======================================================")
    prt_lines.append("BodyID={}".format(body_id))
    for d, document in enumerate(docs):
        indent = d * 4
        indent_str = get_indentation(indent)
        prt_lines.append("Indent={}".format(indent))
        prt_lines.append(indent_str + "MD5={}".format(docs_md5[d]))
        prt_lines.append(indent_str + "Incoming={}".format(docs_incoming[d]))
        prt_lines.append(indent_str + intent_labels)
        prt_lines.append(indent_str + job_type_labels)
        prt_lines.append(indent_str + "^^^^^^^^^^^^^^^^")
        for ln in document["lines"]:
            prt_lines.append(indent_str + ln)
            prt_lines.append(indent_str + "\t" + sent_intent_labels + "\n")
    if append_breaks:
        prt_lines.append("\n\n\n")
    return "\n".join(prt_lines)


trainable_bodies_labelling_friendly = list()
line_level_body_ids = list()
line_level_doc_ids = list()
line_level_senders = list()
all_lines = list()
all_lines_md5 = list()
line_level_doc_md5 = list()
line_level_is_new_doc = list()
doc_level_body_ids = list()
doc_level_doc_ids = list()
doc_level_senders = list()
doc_level_text = list()
doc_level_md5 = list()
doc_level_is_new_doc = list()
doc_level_n_lines = list()
doc_id = 0
for body_id in bodies:
    body_docs = list()
    docs_md5 = list()
    docs_incoming = list()
    for doc in bodies[body_id]:
        sender = doc["sender"]
        doc_lines = doc["lines"]
        is_new_doc = doc["new"]
        n_lines = len(doc_lines)
        if n_lines > 0:
            line_md5 = [nlp.md5(s) for s in doc_lines]
            doc_text = "\n".join(doc_lines)
            doc_md5 = nlp.md5("\n".join(line_md5))
            body_docs.append(doc)
            docs_md5.append(doc_md5)
            docs_incoming.append(sender.find("@haulio.io") == -1)

            line_level_body_ids.extend([body_id] * n_lines)
            line_level_doc_ids.extend([doc_id] * n_lines)
            line_level_senders.extend([sender] * n_lines)
            all_lines.extend(doc_lines)
            all_lines_md5.extend(line_md5)
            line_level_doc_md5.extend([doc_md5] * n_lines)
            line_level_is_new_doc.extend([is_new_doc] * n_lines)

            doc_level_body_ids.append(body_id)
            doc_level_doc_ids.append(doc_id)
            doc_level_senders.append(sender)
            doc_level_text.append(doc_text)
            doc_level_md5.append(doc_md5)
            doc_level_is_new_doc.append(is_new_doc)
            doc_level_n_lines.append(n_lines)
        doc_id += 1
    if (len(body_docs) > 0) and docs_incoming[0]:
        trainable_bodies_labelling_friendly.append(to_labelling_friendly(body_id, body_docs, docs_md5, docs_incoming))
all_lines = np.array(all_lines)
all_lines_md5 = np.array(all_lines_md5)
line_level_doc_md5 = np.array(line_level_doc_md5)
line_level_senders = np.array(line_level_senders)
line_level_n_parts = np.array([len(s.split(" ")) for s in all_lines])


# for i in range(1000):
#     subset = trainable_bodies_labelling_friendly[i*100:(i+1)*100]
#     if len(subset) > 0:
#         with open("data/labelled/{}.html".format(str(i).rjust(3, "0")), "w") as f:
#             for txt in subset:
# #######                f.write(txt)
#     else:
#         break


lines_data = pd.DataFrame({
    "body_id": line_level_body_ids,
    "doc_id": line_level_doc_ids,
    "line": all_lines,
    "line_md5": all_lines_md5,
    "sender": line_level_senders,
    "incoming": [s.find("@haulio.io") == -1 for s in line_level_senders],
    "new_doc": line_level_is_new_doc,
    "doc_md5": line_level_doc_md5,
    "n_parts": line_level_n_parts
})

doc_df = pd.DataFrame({
    "body_id": doc_level_body_ids,
    "doc_id": doc_level_doc_ids,
    "text": doc_level_text,
    "sender": doc_level_senders,
    "incoming": [s.find("@haulio.io") == -1 for s in doc_level_senders],
    "new_doc": doc_level_is_new_doc,
    "n_lines": doc_level_n_lines,
    "doc_md5": doc_level_md5
}, index=doc_level_doc_ids)
doc_df.to_csv("data/doc_df.csv", index=False, encoding="utf-16")
