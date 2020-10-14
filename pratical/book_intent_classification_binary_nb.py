import numpy as np
import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn import svm
from sklearn.linear_model import LogisticRegression, SGDClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix


book_intent_data = pd.read_csv("data/book_intent_binary_classification.csv")

X_train, X_test, y_train, y_test = train_test_split(book_intent_data["text"], book_intent_data["class"], random_state=1, test_size=0.1)

exam_text = [
    "We need a container to be ready at DHL's warehouse on _DATE_. Can it be arranged?",
    "We need a 20 foot container. Is it available?",
    "We are looking for a container for the shipment for IKEA. Can it be arranged?",
    "IKEA requires a container for its shipment on _DATE_. Can it be arranged?",
    "There is a shipment that requires a container for export. Can it be arranged?.",
    "We would like you to arrange a container for our customer to export something.",
    "Can we book a container from IKEA to PSA?",
    "I want a container to be ready and stand by on the coming Wednesday.",
    "Can I book a container for this Friday? I have an import job to do.",
    "Can I have a 20'GP for tomorrow's export at DSO 12 Science Park?",
    "We have an import job from Ang Mo Kio Industrial Park to PSA. We need a 40 foot container.",
    "I want to book a container for Tuesday",
    "Please truck in MT 2 x 40HC on _DATE_ to SANKYU TLH WAREHOUSE 5 TUAS VIEW LANE, _POSTAL_",
    "Please arrange as below. thank you",
    "Kindly request you to make arrangement for this shipment",
    "Please arrange to collect container tomorrow: _DATE_",
    "As Spoken Please Assist to Arrange Export Trucking 2 X 40ft HC Container on _DATE_,refer below The details for Your Kind attention.",
    "Please find the attached docs for 1 x 20'GP container trucking to following premises at :",
    "Please deliver 3 x 40'HC together on Saturday – _DATE_ morning.",
    "1 X 20ft GP to be trucked in at Ikea on _DATE_, please kindly assist.",
    
    "From Geodis, who could have created themselves",
    "Please arrange to truck out the empty container accordingly as below without further delay.",
    "Please ref to attached cartage advice and booking confirmation",
    "Please send _CONT_NO_, _CONT_NO_ to AMS, the rest of 7 containers TLH.",
    "We had transfer the payment to shipping line.",
    "Container number: _CONT_NO_ / 40’HC",
    "Hock Cheong Forwarding @ 1765 Geylang Bahru #01-02 Kallang Distripack.",
    "Please advise container no. once available.",
    "PLEASE ENSURE BOTH PANEL UPRIGHT ITS POSITION UPON YOUR COLLECTION",
    "Please release 100x40RH to Haulio haulier.",
    "As spoken, haulier is still in the midst of collection.",
    "Will update the container numbers later.",
    "Keep you posted again once collected.",
    "Thank you for your understanding.",
    "Please provide asap.",
    "There’s no container details yet.",
    "Noted with thanks",
    "Yard has updated the CMS, kindly check again.",
    "Also, kindly advise on the truck out date too.",
    "I’m checking with he carrier to update on _DATE_."
]
y_exam = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

vectorizer = CountVectorizer(token_pattern=u"(?ui)\\b\\w*[a-z]+\\w*\\b", lowercase=True, stop_words="english")

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

naive_bayes = MultinomialNB()
naive_bayes.fit(X_train_vec, y_train)
nb_y_hat = naive_bayes.predict(X_test_vec)


print("NB Accuracy score: ", accuracy_score(y_test, nb_y_hat))
print("NB Precision score: ", precision_score(y_test, nb_y_hat))
print("NB Recall score: ", recall_score(y_test, nb_y_hat))
print(confusion_matrix(y_test, nb_y_hat))

nb_predict_exam = naive_bayes.predict(vectorizer.transform(exam_text))
print("NB", nb_predict_exam)
print("NB Precision score: ", precision_score(y_exam, nb_predict_exam))
print("NB Recall score: ", recall_score(y_exam, nb_predict_exam))






clr_svm = svm.SVC(C=5000.0, gamma="auto", kernel='rbf').fit(X_train_vec, y_train)
svm_y_hat = clr_svm.predict(X_test_vec)

print("SVM Accuracy score: ", accuracy_score(y_test, svm_y_hat))
print("SVM Precision score: ", precision_score(y_test, svm_y_hat))
print("SVM Recall score: ", recall_score(y_test, svm_y_hat))
print(confusion_matrix(y_test, svm_y_hat))

svm_predict_exam = clr_svm.predict(vectorizer.transform(exam_text))
print("SVM", svm_predict_exam)
print("SVM Precision score: ", precision_score(y_exam, svm_predict_exam))
print("SVM Recall score: ", recall_score(y_exam, svm_predict_exam))


def sigmoid(x):
  return 1 / (1 + np.exp(-x))


def binary_decision(x):
    return x > -0.6


clf_ME = LogisticRegression(random_state=0, solver='liblinear', class_weight='balanced').fit(X_train_vec, y_train)
lr_y_hat = clf_ME.predict(X_test_vec)

print("LR Accuracy score: ", accuracy_score(y_test, lr_y_hat))
print("LR Precision score: ", precision_score(y_test, lr_y_hat))
print("LR Recall score: ", recall_score(y_test, lr_y_hat))
print(confusion_matrix(y_test, lr_y_hat))

prob = sigmoid(clf_ME.decision_function(vectorizer.transform(exam_text)))
lr_predict_exam = (prob > 0.5).astype(int)
print("LR", lr_predict_exam)
print("LR Precision score: ", precision_score(y_exam, lr_predict_exam))
print("LR Recall score: ", recall_score(y_exam, lr_predict_exam))



clf_sgd = SGDClassifier(loss="log", random_state=2).fit(X_train_vec, y_train)
sgd_y_hat = clf_sgd.predict(X_test_vec)

print("SGD Accuracy score: ", accuracy_score(y_test, sgd_y_hat))
print("SGD Precision score: ", precision_score(y_test, sgd_y_hat))
print("SGD Recall score: ", recall_score(y_test, sgd_y_hat))
print(confusion_matrix(y_test, sgd_y_hat))

prob = sigmoid(clf_sgd.decision_function(vectorizer.transform(exam_text)))
sgd_predict_exam = (prob > 0.5).astype(int)
print("SGD", sgd_predict_exam)
print("SGD Precision score: ", precision_score(y_exam, sgd_predict_exam))
print("SGD Recall score: ", recall_score(y_exam, sgd_predict_exam))




hybrid = np.stack([nb_predict_exam, svm_predict_exam, lr_predict_exam, sgd_predict_exam])
hybrid_predict_exam = np.round(np.mean(hybrid, axis=0), 0).astype(int)
print("hybrid", sgd_predict_exam)
print("hybrid Precision score: ", precision_score(y_exam, hybrid_predict_exam))
print("hybrid Recall score: ", recall_score(y_exam, hybrid_predict_exam))





for k in ["linear", "rbf"]:
    for g in ["auto", "scale"]:
        for c in [5000, 10000]:
            print("kernel={}, gamma={}, c={}".format(k, g, c))
            clr_svm = svm.SVC(C=c, gamma=g, kernel=k).fit(X_train_vec, y_train)
            svm_y_hat = clr_svm.predict(X_test_vec)

            print("SVM Accuracy score: ", accuracy_score(y_test, svm_y_hat))
            print("SVM Precision score: ", precision_score(y_test, svm_y_hat))
            print("SVM Recall score: ", recall_score(y_test, svm_y_hat))

            svm_predict_exam = clr_svm.predict(vectorizer.transform(exam_text))
            print("SVM Exam", svm_predict_exam)
            print("SVM Precision score: ", precision_score(y_exam, svm_predict_exam))
            print("SVM Recall score: ", recall_score(y_exam, svm_predict_exam))
            print()
