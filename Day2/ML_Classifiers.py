# -*- coding: utf-8 -*-
"""
Created on Fri Aug 23 17:03:52 2019

@author: isswan
"""


import sklearn
import nltk
import re 
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import accuracy_score
from sklearn import preprocessing
from sklearn import metrics
from sklearn.feature_selection import SelectKBest
from sklearn.feature_extraction.text import TfidfVectorizer #as vectorizer
from sklearn.model_selection import train_test_split
from sklearn.feature_selection import chi2
from sklearn.metrics import precision_score, recall_score,f1_score
from sklearn.linear_model import LogisticRegression

##########################################################################3
##prepare dataset
from os import getcwd, chdir
import pandas as pd
import pickle as pk
fpath = getcwd()
print (fpath)
# Change your path here
chdir(fpath) 


training = pd.read_csv(fpath+"/Data/train.csv", encoding="utf-8")
testing  = pd.read_csv(fpath+"/Data/test.csv", encoding="utf-8")
print (training.head(5))
print (testing.head(5))
print (testing.tail(5))

#Label conversion: Positive to 1,Negative to -1 
train_pos = training[(training.Sentiment == 'positive')]
train_neg = training[(training.Sentiment == 'negative')]
print (train_pos.head(3))
print (train_pos.head(3))

train_pos_list = []
for i,t in train_pos.iterrows():
    train_pos_list.append([t.text.lower(), 1])

train_neg_list = []
for i,t in train_neg.iterrows():
    train_neg_list.append([t.text.lower(), -1])
#Same for test dataset   
test_pos = testing[(testing.Sentiment == 'positive')]
test_neg = testing[(testing.Sentiment == 'negative')]

test_pos_list = []
for i,t in test_pos.iterrows():
    test_pos_list.append([t.text.lower(), 1])

test_neg_list = []
for i,t in test_neg.iterrows():
    test_neg_list.append([t.text.lower(), -1])

#build the two dataset
trainset = train_pos_list + train_neg_list
testset = test_pos_list + test_neg_list

pk.dump(trainset, open(fpath+"/Data/trainset.pk", "wb"))
pk.dump(testset , open(fpath+"/Data/testset.pk", "wb"))

##########################################################3
###Preprocessing 
# seperate the text with labels

X_train = [t[0] for t in trainset]
X_test = [t[0] for t in testset]

Y_train = [t[1] for t in trainset]
Y_test = [t[1] for t in testset]

#Vectorizer the sentences using Tfidf vale
#Make sure test data should be transformed using vectorizer learned from trainning data 
vectorizer = TfidfVectorizer()
train_vectors = vectorizer.fit_transform(X_train)
test_vectors = vectorizer.transform(X_test)

# same feature set
train_vectors.shape
test_vectors.shape


#########################################################
#Apply NB model
clf_NB = MultinomialNB().fit(train_vectors, Y_train)
predNB = clf_NB.predict(test_vectors)
pred = list(predNB)


print(metrics.confusion_matrix(Y_test, pred))
print(metrics.classification_report(Y_test, pred))

#########################################################
# MaxEnt = LogisticRegression
clf_ME = LogisticRegression(random_state=0, solver='lbfgs').fit(train_vectors, Y_train)
predME = clf_ME.predict(test_vectors)
pred = list(predME)
print(metrics.confusion_matrix(Y_test, pred))
print(metrics.classification_report(Y_test, pred))

#####KNN Classifier
def train_knn(X, y, k, weight):
    """
    Create and train the k-nearest neighbor.
    """
    knn = KNeighborsClassifier(n_neighbors = k, weights = weight, metric = 'cosine', algorithm = 'brute')
    knn.fit(X, y)
    return knn


kn = train_knn(train_vectors, Y_train, 20, 'distance')# distance weights - by inverse of distance
predKN = kn.predict(test_vectors)
pred = list(predKN)
print(metrics.confusion_matrix(Y_test, pred))
print(metrics.classification_report(Y_test, pred))


#Apply SVM model
'''
Not all the feature points are needed to define the support vector.
In a way only the most informative feature points help to define the support vector which makes the SVM ideal for high-dimensional classification 
and sparse matrics common in NLP. 
The SVM can also work on feature points that are not linearly separable through kernel transformation of the feature points.
'''

from sklearn import svm
from sklearn.svm import SVC

model_svm = SVC(C=5000.0, gamma="auto", kernel='rbf')
clr_svm = model_svm.fit(train_vectors, Y_train)

    
predicted = clr_svm.predict(test_vectors)
 
print(metrics.confusion_matrix(Y_test, predicted))
print(np.mean(predicted == Y_test) )
print(metrics.classification_report(Y_test, predicted))

#########################################################
#ADD Features - Negation
import re 
def nega_tag(text):
    transformed = re.sub(r"\b(?:never|nothing|nowhere|noone|none|not|haven't|hasn't|hasnt|hadn't|hadnt|can't|cant|couldn't|couldnt|shouldn't|shouldnt|won't|wont|wouldn't|wouldnt|don't|dont|doesn't|doesnt|didn't|didnt|isnt|isn't|aren't|arent|aint|ain't|hardly|seldom)\b[\w\s]+[^\w\s]", lambda match: re.sub(r'(\s+)(\w+)', r'\1NEG_\2', match.group(0)), text, flags=re.IGNORECASE)
    return(transformed)

text = "I don't like that place you keep calling awesome's Hello woerld"
print (nega_tag(text))

# Create a training list which will now contain reviews with Negatively tagged words and their labels
train_set_nega = []

# Append elements to the list
for doc in trainset:
    trans = nega_tag(doc[0])
    lab = doc[1]
    train_set_nega.append([trans, lab])

print(train_set_nega[18])

# Create a testing list which will now contain reviews with Negatively tagged words and their labels
test_set_nega = []

# Append elements to the list
for doc in testset:
    trans = nega_tag(doc[0])
    lab = doc[1]
    test_set_nega.append([trans, lab])

######################################
#Redo - Preprocessing 
# seperate the text with labels


X_nega_train = [t[0] for t in train_set_nega]
X_nega_test = [t[0] for t in test_set_nega]

Y_nega_train = [t[1] for t in train_set_nega]
Y_nega_test = [t[1] for t in test_set_nega]

#Vectorizer the sentences using Tfidf vale
#Make sure test data should be transformed using vectorizer learned from trainning data 
vectorizer = TfidfVectorizer()
train_nega_vectors = vectorizer.fit_transform(X_nega_train)
test_nega_vectors = vectorizer.transform(X_nega_test)

# bigger feature set
train_vectors.shape
test_vectors.shape

train_nega_vectors.shape
test_nega_vectors.shape
########################################

#Re-train NB model
clf_NB = MultinomialNB().fit(train_nega_vectors, Y_nega_train)
predNB = clf_NB.predict(test_nega_vectors)
pred = list(predNB)

print(metrics.confusion_matrix(Y_nega_test, pred))
print(np.mean(pred == Y_nega_test) )
print(metrics.classification_report(Y_nega_test, pred))

#Re-Train ME model
clf_ME = LogisticRegression(random_state=0, solver='lbfgs').fit(train_nega_vectors, Y_nega_train)
predME = clf_ME.predict(test_nega_vectors)
pred = list(predME)
print(metrics.confusion_matrix(Y_test, pred))
print(metrics.classification_report(Y_test, pred))

#Re-train KNN
kn = train_knn(train_nega_vectors, Y_nega_train, 20, 'distance')# distance weights - by inverse of distance
predKN = kn.predict(test_nega_vectors)
pred = list(predKN)
print(metrics.confusion_matrix(Y_nega_test, pred))
print(metrics.classification_report(Y_nega_test, pred))

#Re-train the SVM
model_svm = SVC(C=5000.0, gamma="auto", kernel='rbf')
clr_svm = model_svm.fit(train_nega_vectors, Y_nega_train)

    
predicted_nega = clr_svm.predict(test_nega_vectors)
 
print(metrics.confusion_matrix(Y_nega_test, predicted_nega))
print(np.mean(predicted_nega == Y_nega_test) )
print(metrics.classification_report(Y_nega_test, predicted_nega))

###############################################
##Select K Best features

ch21 = SelectKBest(chi2, k=5000)
# Transform your training and testing datasets accordingly
train_Kbest = ch21.fit_transform(train_nega_vectors, Y_nega_train)
test_Kbest = ch21.transform(test_nega_vectors)

# Train your SVM with the k best selected features
sv = model_svm.fit(train_Kbest, Y_nega_train)
predSVM= sv.predict(test_Kbest)
pred = list(predSVM)

print(metrics.confusion_matrix(Y_nega_test, pred))
print(np.mean(predSVM == Y_nega_test) )
print(metrics.classification_report(Y_nega_test, pred))

selected_features = list(np.array(vectorizer.get_feature_names())[ch21.get_support()])
print (selected_features)
