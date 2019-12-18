# -*- coding: utf-8 -*-
"""
Created on Thu Aug 15 10:17:38 2019

@author: isswan
"""
#pip install tabulate
from tabulate import tabulate
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from gensim.models.word2vec import Word2Vec 
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import cross_val_predict
from sklearn.model_selection import StratifiedShuffleSplit
import sklearn
import nltk
import re 
from sklearn.svm import SVC
from sklearn.metrics import classification_report
from sklearn import preprocessing
from sklearn import metrics
from sklearn.feature_selection import SelectKBest
from sklearn.feature_selection import chi2
from sklearn.metrics import precision_score, recall_score,f1_score


from os import getcwd, chdir
import pandas as pd
import pickle as pk

encoding="utf-8"



fpath = getcwd()
print (fpath)
# Change your path here
chdir(fpath) 

###################################################
#Data Preparation
###################################################
trainset = pk.load(open(fpath+"\\pickle\\trainset.pk","rb"))
testset = pk.load(open(fpath+"\\pickle\\testset.pk","rb"))
GLOVE_6B_100D_PATH = fpath+"\\Data\\glove.6B.100d.txt"

X_train = [t[0].split() for t in trainset]
X_test = [t[0].split() for t in testset]

X = X_train + X_test

Y_train = [t[1] for t in trainset]
Y_test = [t[1] for t in testset]

y = Y_train + Y_test

X[:1]
len(X)

X, y = np.array(X), np.array(y)
####################################################
#MeanEmbeddingVectorizer define the way to represent docs using word vectors

class MeanEmbeddingVectorizer(object):
    def __init__(self, word2vec):
        self.word2vec = word2vec
        if len(word2vec)>0:
            self.dim=len(word2vec[next(iter(glove_small))])
        else:
            self.dim=0
            
    def fit(self, X, y):
        return self 

    def transform(self, X):
        return np.array([
            np.mean([self.word2vec[w] for w in words if w in self.word2vec] 
                    or [np.zeros(self.dim)], axis=0)
            for words in X
        ])
###################################################
#Prepare word embeddings from GLOVE
import numpy as np
with open(GLOVE_6B_100D_PATH, "rb") as lines:
    wvec = {line.split()[0].decode(encoding): np.array(line.split()[1:],dtype=np.float32)
               for line in lines}


# reading glove files, this may take a while
# we're reading line by line and only saving vectors
# that correspond to words from our data set
import struct 

glove_small = {}
all_words = set(w for words in X for w in words)

print(len(all_words))

with open(GLOVE_6B_100D_PATH, "rb") as infile:
    for line in infile:
        parts = line.split()
        word = parts[0].decode(encoding)
        if (word in all_words):
            nums=np.array(parts[1:], dtype=np.float32)
            glove_small[word] = nums

###################################################
#Prepare word embeddings by training from dataset
model = Word2Vec(X, size=300, window=5, min_count=2, workers=2)
w2v = {w: vec for w, vec in zip(model.wv.index2word, model.wv.syn0)}
###################################################
#define the competing models 

# SVM + tfidf based bag-of-words features
svc_tfidf = Pipeline([("tfidf_vectorizer", TfidfVectorizer(analyzer=lambda x: x)), ("linear svc", SVC(kernel="linear"))])

# SVM + vec_from_dataset + MeanEmbedding
svc_w2v = Pipeline([("word2vec vectorizer", MeanEmbeddingVectorizer(w2v)), ("linear svc", SVC(kernel="linear"))])

# SVM + GLOVE vectors + MeanEmbedding
svc_glove_small = Pipeline([("glove vectorizer", MeanEmbeddingVectorizer(glove_small)), ("linear svc", SVC(kernel="linear"))])


# benchmark all the models
all_models = [
    ("svc_tfidf", svc_tfidf),
    ("svc_w2v", svc_w2v),
    ("svc_glove_small",svc_glove_small)
]

##############################################
#Predict using tfidf feature
svc_model = svc_tfidf.fit(X_train,Y_train)
svc_pred = svc_model.predict(X_test)
conf_mat = confusion_matrix(Y_test, svc_pred)
print ("SVC:\n",conf_mat)
print(metrics.classification_report(Y_test, svc_pred))

#Predict using pre-trained glove model
svc_glove_model = svc_glove_small.fit(X_train,Y_train)
svc_glove_pred = svc_glove_model.predict(X_test)
conf_mat = confusion_matrix(Y_test, svc_glove_pred)
print ("SVC_glove:\n",conf_mat)
print(metrics.classification_report(Y_test, svc_glove_pred))


#Predict using self-trained word2vec
svc_w2v_model = svc_w2v.fit(X_train,Y_train)
svc_w2v_pred = svc_w2v_model.predict(X_test)
conf_mat = confusion_matrix(Y_test, svc_w2v_pred)
print ("SVC_w2v:\n",conf_mat)
print(metrics.classification_report(Y_test, svc_w2v_pred))

##################################################
##how the ranking depends on the amount of training data
def benchmark(model, X, y, n,X_test,y_test):
    scores = []
    sss = StratifiedShuffleSplit(n_splits=5, train_size=n,test_size =len(y)-n )
    
    for train, test in sss.split(X, y):
        X_train = X[train]
        y_train = y[train]
        scores.append(accuracy_score(model.fit(X_train, y_train).predict(X_test), y_test))
        break
    return np.mean(scores)

train_sizes = [1000,5000,10000,15000,17900]
table = []
for name, model in all_models:
    for n in train_sizes:
        table.append({'model': name, 
                      'accuracy': benchmark(model, np.array(X_train), np.array(Y_train), n,X_test, Y_test), 
                      'train_size': n})
df = pd.DataFrame(table)

plt.figure(figsize=(15, 6))
fig = sns.pointplot(x='train_size', y='accuracy', hue='model', 
                    data=df[df.model.map(lambda x: x in ["svc_tfidf", "svc_w2v", "svc_glove_small", ])])
sns.set_context("notebook", font_scale=1.5)
fig.set(ylabel="accuracy")
fig.set(xlabel="labeled training examples")
fig.set(title="R8 benchmark")
fig.set(ylabel="accuracy")

###################################################
# Cross validation results for all models
#unsorted_scores = [(name, cross_val_score(model, X, y, cv=5).mean()) for name, model in all_models]
#scores = sorted(unsorted_scores, key=lambda x: -x[1])
#print (tabulate(scores, floatfmt=".4f", headers=("model", 'score')))


