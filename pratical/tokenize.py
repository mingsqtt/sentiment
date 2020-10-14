import random
from itertools import chain
import numpy as np
import os

from tqdm import tqdm
from gensim.corpora import Dictionary

from nltk import word_tokenize, sent_tokenize

from gensim.corpora.dictionary import Dictionary

from sklearn.model_selection import train_test_split

from lmpylib.nlp import md5, search_pattern


all_doc_text_by_md5 = dict()
entire_corpus = ""
for b in bodies:
    for doc in bodies[b]:
        current_doc_text = ""
        for line in doc["replaced_lines"]:
            current_doc_text += line + "\n"

        if len(current_doc_text) > 0:
            digest = md5(current_doc_text)
            if not all_doc_text_by_md5.__contains__(digest):
                all_doc_text_by_md5[digest] = current_doc_text.rstrip("\n")
                entire_corpus += current_doc_text
        break
print("no. of docs: ", len(all_doc_text_by_md5))


tokenized_docs = [word_tokenize(doc_txt) for doc_txt in all_doc_text_by_md5.values()]
uniq_tokens = set(chain(*tokenized_docs))





print("vocabulary size: ", len(uniq_tokens))

term_df = pd.DataFrame({
    "token": list(chain(*tokenized_docs)),
    "tf": 1
})
tf = term_df.groupby("token").count().sort_values("tf", ascending=False)
summary(tf)
summary(tf["tf"] > 11)
summary(tf["tf"] < 5)
tf.loc[tf["tf"] > 11, :]
tf.loc[(tf["tf"] >= 5) & (tf["tf"] <= 11), :].index.to_list()
tf.loc[tf["tf"] < 5, :]
hist(tf["tf"], range=(100, 10000), bins=50)


for doc_txt in all_doc_text_by_md5.values():
    if doc_txt.find("23/11-") >= 0:
        print(doc_txt, "\n")

for b in bodies:
    for doc in bodies[b]:
        replaced_text, ori_text = "", ""
        for line in doc["replaced_lines"]:
            replaced_text += line + "\n"
        for line in doc["lines"]:
            ori_text += line + "\n"

        if replaced_text.find("_TIME__TIME_-") >= 0:
            print(replaced_text)
            print(ori_text)
        break


replace_patterns("\n26-May-20\n2\nTLLU5640408")

txt = "0- hello -mygod ABC/DEF/ of /XXX YYY-\nGood"

