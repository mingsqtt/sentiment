import numpy as np
import pandas as pd
import re
import pickle

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn import svm
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.ensemble import VotingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix, classification_report
from sklearn.feature_selection import SelectKBest, chi2

from scipy.stats import mode
from scipy.special import softmax

from lmpylib.core import *

update_intent_data = pd.read_csv("data/update_intent_data.csv")
update_intent_data["class"] = 0
update_intent_data.loc[update_intent_data["update"] == 1, "class"] = 1

X_train, X_test, y_train, y_test = train_test_split(update_intent_data["text"].values, update_intent_data["class"].values, random_state=1, test_size=0.1)

pos_exam_corpus = [
    "There is a change in the schedule.",
    "Please noet that the vessel has delayed to _DATE_.",
    "The vessel has delayed. Can the trucking be rescheduled?",
    "The container number is _CONT_NO_.",
    "The delivery address is 12 Science Park Drive, _POSTAL_",
    "Please deliver to 12 Science Park Drive, DSO",
    "Please truck in on _DATE_.",
    "The truck in date is confirmed to be _DATE_.",
    "We need 3 X 20'GP.",
    "4 containers please.",
    "It is 20'GP instead of 40'HC.",
    "The previously booked container is wrong. Please arrange 2 X 20'GP instead.",
    "Please take note that the delivery address has been changed to 639 Jurong West St 61",
    "Container number: _CONT_NO_ / 40'HC",
    "Vessel is Titanic",
    "Vessel/Voyage is Titanic/_CODE_",
    "Delivery location is at Hock Cheong Forwarding @ 1765 Geylang Bahru _UNIT_LEVEL_ Kallang Distripack.",
    "Can we change the delivery location?",
    "The vessel ETA is now changed to _DATE_. There may be further delay.",
    "Please update the ETA to tomorrow.",
]

X_test = np.concatenate([pos_exam_corpus, X_test])
y_test = np.concatenate([np.repeat(1, len(pos_exam_corpus)), y_test])


# unigram_vectorizer = CountVectorizer(token_pattern=u"(?ui)\\b\\w*[a-z]+\\w*\\b", lowercase=True, stop_words=["is", "the", "a", "for"], ngram_range=(1, 1))
# unigram = unigram_vectorizer.fit_transform(X_train)
# len(unigram_vectorizer.vocabulary_)
# dir(unigram_vectorizer)
# mtx = unigram.toarray()
# term_freq = np.sum(mtx, axis=0)
# high_fre_term_indices = set(np.argwhere(term_freq > 20).flatten())
# for term in unigram_vectorizer.vocabulary_:
#     term_ind = unigram_vectorizer.vocabulary_[term]
#     if high_fre_term_indices.__contains__(term_ind):
#         print(term, term_freq[term_ind])
# hist(term_freq, bins=50, range=(10, 100))


vectorizer = CountVectorizer(token_pattern=u"(?ui)\\b\\w*[a-z]+\\w*\\b", lowercase=True, stop_words=["is", "the", "a", "for", "kindly", "by", "thank", "thanks", "so", "that", "be", "i", "we", "s", "just", "system", "hcp", "my"], ngram_range=(1, 2))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

naive_bayes = MultinomialNB()
naive_bayes.fit(X_train_vec, y_train)
nb_y_hat = naive_bayes.predict(X_test_vec)


print("NB Test score:\n", classification_report(y_test, nb_y_hat, labels=[1, 0], target_names=["update", "others"]))
print("NB Exam", nb_y_hat[:len(pos_exam_corpus)])
print("NB Exam Recall", np.sum(nb_y_hat[:len(pos_exam_corpus)]) / len(pos_exam_corpus))
print(confusion_matrix(y_test, nb_y_hat))

with open("models/update_intent_naive_bayes.pickle", "wb") as f:
    pickle.dump(naive_bayes, f)
with open("models/update_intent_naive_bayes_vectorizer.pickle", "wb") as f:
    pickle.dump(vectorizer, f)



def sigmoid(x):
  return 1 / (1 + np.exp(-x))


def binary_decision(x):
    return x > -0.6


vectorizer = TfidfVectorizer(token_pattern=u"(?ui)\\b\\w*[a-z]+\\w*\\b", lowercase=True, stop_words=None, ngram_range=(1, 1))

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

cls_lr = LogisticRegression(random_state=0, solver='lbfgs').fit(X_train_vec, y_train)
prob = sigmoid(cls_lr.decision_function(X_test_vec))
lr_y_hat = (prob > 0.4).astype(int)


print("LR Test score:\n", classification_report(y_test, lr_y_hat, labels=[1, 0], target_names=["update", "others"]))
print("LR Exam", lr_y_hat[:len(pos_exam_corpus)])
print("LR Exam Recall", np.sum(lr_y_hat[:len(pos_exam_corpus)]) / len(pos_exam_corpus))
print(confusion_matrix(y_test, lr_y_hat))

with open("models/update_intent_cls_lr.pickle", "wb") as f:
    pickle.dump(cls_lr, f)
with open("models/update_intent_cls_lr_vectorizer.pickle", "wb") as f:
    pickle.dump(vectorizer, f)




vectorizer = TfidfVectorizer(token_pattern=u"(?ui)\\b\\w*[a-z]+\\w*\\b", lowercase=True, stop_words=None, ngram_range=(1, 1))
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)


clf_forest = RandomForestClassifier(n_estimators=100, random_state=2).fit(X_train_vec, y_train)
forest_y_hat = clf_forest.predict(X_test_vec)

print("Forest Test score:\n", classification_report(y_test, forest_y_hat, labels=[1, 0], target_names=["update", "others"]))
print("Forest Exam", forest_y_hat[:len(pos_exam_corpus)])
print("Forest Exam Recall", np.sum(forest_y_hat[:len(pos_exam_corpus)]) / len(pos_exam_corpus))
print(confusion_matrix(y_test, forest_y_hat))

with open("models/update_intent_clf_forest.pickle", "wb") as f:
    pickle.dump(clf_forest, f)
with open("models/update_intent_clf_forest_vectorizer.pickle", "wb") as f:
    pickle.dump(vectorizer, f)



# combined = np.stack([nb_y_hat, nb2_y_hat, forest_y_hat])
# voting_test = mode(combined, axis=0)[0][0]

stacked = np.stack([nb_y_hat, lr_y_hat, forest_y_hat])
print(stacked[:, :len(pos_exam_corpus)])
print(np.round(np.mean(stacked, axis=0), 1)[:len(pos_exam_corpus)])
voting_test = (nb_y_hat.astype(bool) | lr_y_hat.astype(bool) | forest_y_hat.astype(bool)).astype(int)
# voting_test = np.round(np.mean(stacked, axis=0), 0).astype(int)


print("Hybrid Test score:\n", classification_report(y_test, voting_test, labels=[1, 0], target_names=["update", "others"]))
print("Hybrid Exam", voting_test[:len(pos_exam_corpus)])
print("Hybrid Exam Recall", np.sum(voting_test[:len(pos_exam_corpus)]) / len(pos_exam_corpus))
print(confusion_matrix(y_test, voting_test))





def is_update_later_intent(line):
    if re.search("(?i)(update|provide|give)( \w+)* once (available|have|receive|confirmed|ready|done|approved)", line) is not None:
        return True
    elif re.search("(?i)will (update|provide|give)( \w+){0,4} ((on (monday|tuesday|wednesday|thursday|friday|saturday|sunday))|by today|by tomorrow|by next|tomorrow|next|later|soon|again|accordingly|shortly)", line) is not None:
        return True
    elif re.search("(?i)once (available|have|receive|confirmed).*will (update|provide|give)", line) is not None:
        return True
    return False

n_miss = 0
for l, line in enumerate(update_intent_data.loc[update_intent_data["update_later"] != 1, "text"].values):
    if is_update_later_intent(line):
        n_miss += 1
        print(line)
print(n_miss)


later
not available
unavailable
becomes available
will advise/inform/update you
