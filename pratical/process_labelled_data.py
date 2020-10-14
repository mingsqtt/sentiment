from lmpylib.core import *
import spacy
from spacy.util import minibatch, compounding
import random
from sklearn.model_selection import train_test_split
import re
from nltk import word_tokenize

from lmpylib.nlp import search_pattern, search_all_dates, search_all_times, search_date_pattern, search_time_pattern


valid_ner_classes = set(['ADDR',
 'APPOINTMENT',
 'ARRAY',
 'BAY',
 'BLOCK',
 'BLOCK_STREET',
 'CARRIER',
 'CODE',
 'COMPANY',
 'CONTAINER_NO',
 'CUSTOMER',
 'DATE',
 'DATETIME',
 'DAY_TIME',
 'DEPARTMENT',
 'DEPOT',
 'ETA',
 'FACILITY',
 'FIELD_LABEL',
 'FIELD_NAME',
 'FROM_LOC',
 'HAULIER',
 'HOLIDAY',
 'HOUR',
 'JOB_CODE',
 'LEVEL',
 'OFFHIRE_REF',
 'PERSON',
 'PIC',
 'PLACE',
 'PORT',
 'POSTAL',
 'QTY',
 'QTY_SPE',
 'SHIPPER',
 'SPE',
 'TABLE_COL',
 'TABLE_VAL',
 'TEL',
 'TIME',
 'TO_LOC',
 'DELIVERY_LOC',
 'TRUCKIN_TIME',
 'TRUCKOUT_TIME',
 'UNIT',
 'VESSEL',
 'VESSEL_VOYAGE',
 'VOYAGE',
 'VESSEL_CODE',
 'VOYAGE_CODE',
 'WEIGHT'])


def get_class(text, tag="p"):
    a = text.find("<" + tag + ">")
    if a > 0:
        b = text.find("</" + tag + ">")
        return text[a+3:b]
    else:
        return None


def get_sequence_labels(text, valid_classes=None, return_spacy_format=False):
    if (text.find("</") > 0) and (text.find(">") > 0):
        if valid_classes is not None:
            valid_classes = set(valid_classes)

        ori_text = ""
        n_char = len(text)
        i, ori_i = 0, 0
        tag_stack = list()
        labels = list()
        while i < n_char:
            ch = text[i]
            if ch == "<":
                ind = text.find(">", i + 1)
                if ind > 0:
                    if (i + 1 < n_char) and (text[i + 1] == "/"):
                        closing_tag = text[(i + 2):ind].upper()
                        if closing_tag.find("<") == -1:
                            if (len(tag_stack) > 0) and (tag_stack[len(tag_stack) - 1][0] == closing_tag):
                                labels.append(tag_stack.pop())
                                i += 3 + len(closing_tag)
                                continue
                            else:
                                raise Exception("Expecting opening tag " + closing_tag + " but not found: " + text + "\n" + str(tag_stack))
                    else:
                        opening_tag = text[(i + 1):ind].upper()
                        if (opening_tag.find("MAILTO") == -1) and (opening_tag.find("HTTP") == -1) and (opening_tag.find("<") == -1):
                            if (valid_classes is not None) and (not valid_classes.__contains__(opening_tag)):
                                raise Exception(
                                    "<" + opening_tag + "> tag is not allowed: " + text + "\n" + (str(tag_stack) if len(tag_stack) > 0 else ""))
                            else:
                                tag_stack.append([opening_tag, ori_i, ori_i, ""])
                                i += 2 + len(opening_tag)
                                continue

            ori_text += ch
            for tag in tag_stack:
                tag[2] += 1
                tag[3] += ch
            i += 1
            ori_i += 1

        if return_spacy_format:
            annotations = list()
            for label in labels:
                annotations.append((label[1], label[2], label[0]))
            return ori_text, {"entities": annotations}
        else:
            return ori_text, labels
    else:
        return text, []


def process_lines(lines, lines_intents):
    line_intent_labels = []
    doc_text, seq_labels = get_sequence_labels("\n".join(lines), valid_classes=valid_ner_classes)
    lns = doc_text.split("\n")
    if len(lns) == len(lines_intents):
        for l0, intent_ln in enumerate(lines_intents):
            intent = get_class(intent_ln)
            if intent is not None:
                line_intent_labels.append((intent, lns[l0]))
    else:
        raise Exception("doc has {} lines but intents has {} lines: {}, {}, {}, {}".format(len(lns), len(lines_intents), lines, lns, lines_intents, doc_text))
    return doc_text, seq_labels, line_intent_labels


def process_file(file_lines):
    body_id, indent, doc_begin, doc_class, jt_class, doc_lines, intent_lines = None, None, False, None, None, None, None
    for line in file_lines:
        if (line == "") or (line == "\n"):
            pass
        elif line.strip("\n") == "======================================================= BODY =======================================================":
            body_id = None
            doc_begin = False
            if doc_lines is not None:
                doc_text, seq_labels, intent_labels = process_lines(doc_lines, intent_lines)
                if len(seq_labels) > 0:
                    ner_labelled_docs.append((doc_text, {"entities":  [(t[1], t[2], t[0].upper()) for t in seq_labels]}))
                if doc_class is not None:
                    intent_labelled_docs.append((doc_class, jt_class, doc_text))
                if len(intent_labels) > 0:
                    intent_labelled_lines.extend(intent_labels)
        elif line.find("Indent=") == 0:
            indent = int(line[7:])
            doc_begin = False
            if doc_lines is not None:
                doc_text, seq_labels, intent_labels = process_lines(doc_lines, intent_lines)
                if len(seq_labels) > 0:
                    ner_labelled_docs.append((doc_text, {"entities":  [(t[1], t[2], t[0].upper()) for t in seq_labels]}))
                if doc_class is not None:
                    intent_labelled_docs.append((doc_class, jt_class, doc_text))
                if len(intent_labels) > 0:
                    intent_labelled_lines.extend(intent_labels)
        elif not doc_begin:
            if (body_id is None) and (line.find("BodyID=") == 0):
                body_id = int(line[7:])
            elif (line.find("MD5=") == indent) or (line.find("Incoming=") == indent):
                pass
            elif line.find("<intent>") == indent:
                doc_class = get_class(line)
            elif line.find("<jt>") == indent:
                jt_class = get_class(line)
            elif line.find("^^^^^^^^^^^^^^^^") == indent:
                doc_begin = True
                doc_lines = []
                intent_lines = []
        else:
            line_corr = line[indent:].strip('\n')
            if (line_corr.find("    <intent>") == 0) or (line_corr.find("\t<intent>") == 0):
                intent_lines.append(line_corr)
            else:
                doc_lines.append(line_corr)


intent_labelled_docs = []
ner_labelled_docs = []
intent_labelled_lines = []

for file_name in ["000", "001", "002", "003", "004", "390", "391", "392", "393", "394"]:
    print(file_name)
    with open("data/labelled/{}.html".format(file_name), encoding="utf-8") as f:
        process_file(f.readlines())
summary([t[0] for t in intent_labelled_lines])

unique = set()
for tup in intent_labelled_lines:
    if tup[0] == "book":
        if not unique.__contains__(tup[1]):
            unique.add(tup[1])
            print(len(unique), tup[1])

targeted_ner_classes = set(["VESSEL_VOYAGE"])
targeted_ner_labelled_docs = list()
kk = list()
for d in ner_labelled_docs:
    entities = list()
    for tup in d[1]["entities"]:
        if targeted_ner_classes.__contains__(tup[2]):
            entities.append(tup)
    if len(entities) > 0:
        # print(d[0])
        targeted_ner_labelled_docs.append((d[0], {"entities": entities}))
        for lbl in entities:
            txt = d[0][lbl[0]:lbl[1]]
            print(txt)
            kk.append(txt)
            print()

set(kk)


ss = {}
for d in ner_labelled_docs:
    for tup in d[1]["entities"]:
        if not ss.__contains__(tup[2]):
            ss[tup[2]] = 1
        else:
            ss[tup[2]] = ss[tup[2]] + 1


def create_augmented_spacy_ner_data(input_ner_labelled_docs, ner_classes, replacement_data, n_iter, keep_trainable_classes=None):
    ner_classes = np.array(ner_classes)
    if keep_trainable_classes is not None:
        keep_trainable_classes = np.array(keep_trainable_classes)

    docs = list()
    for doc in input_ner_labelled_docs:
        for tup in doc[1]["entities"]:
            if np.any(tup[2] == ner_classes):
                docs.append(doc)
                break

    augmented_data = list()
    for it in range(n_iter):
        for doc in docs:
            processable_labels = list()
            for tup in doc[1]["entities"]:
                processable_labels.append([tup[0], tup[1], tup[2], np.any(tup[2] == ner_classes)])

            new_text = doc[0]
            for t in range(len(processable_labels)):
                lbl = processable_labels[t]
                if not lbl[3]:
                    continue
                cur_start = lbl[0]
                cur_end = lbl[1]
                cur_len = cur_end - cur_start
                cur_class = lbl[2]
                replacement = str(np.random.choice(replacement_data[cur_class], 1)[0])
                new_len = len(replacement)
                new_text = new_text[:cur_start] + replacement + new_text[cur_end:]
                if new_len != cur_len:
                    len_diff = new_len - cur_len
                    for t0 in range(len(processable_labels)):
                        lbl0 = processable_labels[t0]
                        if lbl0[0] >= cur_end:
                            lbl0[0] += len_diff
                        if lbl0[1] >= cur_end:
                            lbl0[1] += len_diff

            new_annotations = list()
            for lbl in processable_labels:
                if (keep_trainable_classes is None) or (np.any(keep_trainable_classes == lbl[2])):
                    new_annotations.append((lbl[0], lbl[1], lbl[2]))
            augmented_data.append((new_text, {"entities": new_annotations}))
    return augmented_data


sample_container_numbers = pd.read_csv("data/container_numbers.csv")["container_no"].values
vessel_voyage_codes = pd.read_csv("data/crawl-berthing-schedule.csv")
vessel_codes = vessel_voyage_codes["vessel"].unique()
voyage_codes = vessel_voyage_codes["voyage_in"].unique()

np.any(vessel_codes == "MP THE MCGINEST")

augmented_vsl_voyage_ner_data = create_augmented_ner_data(ner_labelled_docs, ["VESSEL_CODE", "VOYAGE_CODE"],
                                                            {
                                                                "VESSEL_CODE": vessel_codes,
                                                                "VOYAGE_CODE": voyage_codes
                                                            }, 1,  ["VESSEL", "VOYAGE"])



from sklearn.metrics import confusion_matrix
from sklearn import metrics



actual = [(12, 19, "L1"), (22, 24, "L2"), (35, 39, "L3")]
pred = [(22, 24, "L2"), (35, 36, "L3"), (37, 49, "L3"), (52, 59, "L5")]

actual = [("li ming", "L1"), ("tian tian", "L2"), ("wang yuan", "L3")]
pred = [("tian tian", "L2"), ("wang", "L3"), ("wang yuan", "L3"), ("zhu", "L1")]


def eval_seqential_labelling_by_span(doc_actual, doc_pred, partial_match_score=0.5):
    true_pos, false_pos = 0, 0
    n_actual = len(doc_actual)
    n_pred = len(doc_pred)
    if (n_pred > 0) and (n_actual > 0):
        for y_hat in doc_pred:
            y_hat_start = y_hat[0]
            y_hat_end = y_hat[1]
            y_hat_class = y_hat[2]

            for y in doc_actual:
                y_start = y[0]
                y_end = y[1]
                y_class = y[2]
                if y_class == y_hat_class:
                    if (y_start == y_hat_start) and (y_end == y_hat_end):
                        true_pos += 1
                        break
                    elif (y_start <= y_hat_start) and (y_end >= y_hat_end):
                        true_pos += partial_match_score
                        break
            else:
                false_pos += 1

        precision = round(true_pos / n_pred, 3)
        recall = round(true_pos / n_actual, 3)
        if (precision + recall) > 0:
            f1 = round(2 * precision * recall / (precision + recall), 5)
        else:
            f1 = 0
    elif (n_pred == 0) and (n_actual == 0):
        precision = 1
        recall = 1
        f1 = 1
    else:
        precision = 0
        recall = 0
        f1 = 0
    return precision, recall, f1


def eval_seqential_labelling_by_text(doc_actual, doc_pred, partial_match_score=0.5):
    true_pos, false_pos = 0, 0
    n_actual = len(doc_actual)
    n_pred = len(doc_pred)
    if (n_pred > 0) and (n_actual > 0):
        for y_hat in doc_pred:
            y_hat_text = y_hat[0]
            y_hat_class = y_hat[1]

            for y in doc_actual:
                y_text = y[0]
                y_class = y[1]
                if y_class == y_hat_class:
                    if y_text == y_hat_text:
                        true_pos += 1
                        break
                    elif y_text.find(y_hat_text) >= 0:
                        true_pos += partial_match_score
                        break
            else:
                false_pos += 1

        precision = round(true_pos / n_pred, 3)
        recall = round(true_pos / n_actual, 3)
        if (precision + recall) > 0:
            f1 = round(2 * precision * recall / (precision + recall), 5)
        else:
            f1 = 0
    elif (n_pred == 0) and (n_actual == 0):
        precision = 1
        recall = 1
        f1 = 1
    else:
        precision = 0
        recall = 0
        f1 = 0
    return precision, recall, f1


def eval_seqential_labelling(actuals, predicts, partial_match_score=0.5, return_mean=True):
    n_actuals = len(actuals)
    n_predicts = len(predicts)
    assert n_actuals == n_predicts, "Length of actuals and predicts should be same, but got ({}, {})".format(n_actuals, n_predicts)

    if n_actuals > 0:
        by_text = True
        for doc in actuals:
            if len(doc) > 0:
                if (len(doc[0]) == 3) and (type(doc[0][0]) == int):
                    by_text = False
                    break
                elif (len(doc[0]) == 2) and (type(doc[0][0]) == str):
                    by_text = True
                    break
                else:
                    assert 1 == 0, "Invalid labelling, expected (text, class) or (start, end, class)"

        precisions, recalls, f1s = np.zeros(n_actuals), np.zeros(n_actuals), np.zeros(n_actuals)
        for i in range(n_actuals):
            if by_text:
                precision, recall, f1 = eval_seqential_labelling_by_text(actuals[i], predicts[i], partial_match_score)
            else:
                precision, recall, f1 = eval_seqential_labelling_by_span(actuals[i], predicts[i], partial_match_score)
            precisions[i] = precision
            recalls[i] = recall
            f1s[i] = f1
        if return_mean:
            return precisions.mean(), recalls.mean(), f1s.mean()
        else:
            return precisions, recalls, f1s
    else:
        return None, None, None




