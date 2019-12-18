# -*- coding: utf-8 -*-
"""
Created on Thu Aug 22 17:19:30 2019
This workshop largely focuses on classification techniques that are used in sentiment analysis. 
Remember sentiment analysis consists of 3 main steps.
 The first is the sourcing and collection of textual data. 
 The second step is the training and classification of the textual data to obtain the sentiment scores. 
 The 3rd step which will be covered on Day 4 is the visualisation and communication of the sentiment scores.
@author: isswan
"""

###############################
#Data Prepration 
# Set your working directory
from os import getcwd, chdir
import pandas as pd
import pickle as pk
fpath = getcwd()
print (fpath)
# Change your path here
chdir(fpath) 


#######################################################################
#reading in another set of data
poslines = open(fpath+"/Data/rt-polarity.utf8.pos",'r',encoding="utf-8").read().splitlines()
neglines = open(fpath+"/Data/rt-polarity-utf8.neg",'r').read().splitlines()

print ("No of positive reviews " + str(len(poslines)))
print ("No of negative reviews " + str(len(neglines)))


# There is a total of 5331 positives and negatives
# Lets take the first N as training set, and leave the rest for validation
N=4800
poslinesTrain = poslines[:N]
neglinesTrain = neglines[:N]
poslinesTest = poslines[N:]
neglinesTest = neglines[N:]

# Create the train set and the test set by attaching labels to text to form a 
# list of tupes (sentence, label). Labels are 1 for positive, -1 for negatives
trainset = [(x,1) for x in poslinesTrain] + [(x,-1) for x in neglinesTrain]
testset = [(x,1) for x in poslinesTest] + [(x,-1) for x in neglinesTest]
#######################################################################
#build a Lexicon Classifier (I)
# We use it for a Lexicon classifier which is essentially count good and bad words from the reviews. 
# The model learns the all the frequencies of a paticular word appearing in Pos/Neg group

poswords = {} # this dictionary will store counts for every word in positives
negwords = {} # and negatives
for line, label in trainset: # for every sentence and its label
	for word in line.split(): # for every word in the sentence
		# increment the counts for this word based on the label
    #Finaly we have the dictionrary:
    #   for each word, how many times does it appear in Pos/Neg group  
		if label == 1: poswords[word] = poswords.get(word,0) + 1
		else: negwords[word] = negwords.get(word, 0) + 1
        
print ("No of negative words in trainset " + str(len(negwords)))
print ("No of positive words in trainset " + str(len(poswords)))

posFreqs = {k: poswords[k] for k in list(poswords)[:5]}
print (posFreqs)
negFreqs = {k: negwords[k] for k in list(negwords)[:5]}
print (negFreqs)

#######################################################################
#The classifier will make judgement based on the posFreq(w)/(posFreq(w)+negFreq(w))
#Apply the classifier on top of testing dataset

wrong = 0 # will store the number of misclassifications
pred_list = []
actual = []
for line, label in testset:
	totpos, totneg = 0.0,0.0
	for word in line.split():
		# Get the (+1 smooth'd) number of counts this word occurs in each class
		#smoothing is done in case this word isn't in train set, so that there
		# is no danger in dividing by 0 later when we do a/(a+b)
		a = poswords.get(word, 0.0) + 1.0
		b = negwords.get(word, 0.0) + 1.0
		#increment our score counter for each class, based on this word
		totpos+=a/(a+b)
		totneg+=b/(a+b)
	#create prediction based on counter values
	prediction=1
	if totneg>totpos: prediction = -1
	pred_list.append(prediction)
	actual.append(label)
	if prediction!=label:
		wrong+=1
		print ('ERROR: %s posscore = %.2f negscore=%.2f' % (line, totpos, totneg))
	else:
		pass
        #print 'CORRECT: %s posscore=%.2f negscore=%.2f' % (line, totpos, totneg)
        
print ('error rate is %f' % (1.0*wrong/len(testset),))
print ('No of wrongs ' + str(wrong))
print ('Size of test set ' + str(len(testset)))

"""
Note down the error rate. The 'correct' rate is already quite high for a simple lexicon classifier. 
Read through some of the wrongly classified ones and can you understand why they are wrongly classified?
 What do you think a high score should be? 
ERROR: it's a big idea , but the film itself is small and shriveled .  posscore = 7.01 negscore=6.99
ERROR: the story alone could force you to scratch a hole in your head .  posscore = 7.34 negscore=6.66
"""
######################################################################
#NLTK Classifier
#In this section, we do the same for a lexicon classifier. 
#This time round, we use as the training set a labelled corpus "Sentiwordnet.txt" from NLTK. 
#The NLTK is a popular open-source text mining tool in Python. 
#Other popular tools include the Stanford NLP and OpenNLP.
#

from nltk.corpus import sentiwordnet as swn
from scipy import mean
from nltk.tokenize import word_tokenize as wt


synsets = swn.senti_synsets('fast')
    
for syn in swn.senti_synsets('fast'):
    print (str(syn))

##Caculate the overall polarity of given word  
    ## mean of Pos/Neg score by averaging the polarity of all the synonyms 
    ## max by selecting the max
def get_pos_neg_score(word, metric):
    posi=[0.0]
    negi=[0.0]
    synsets = swn.senti_synsets(word)
    for syn in synsets:
        posi.append(syn.pos_score())
        negi.append(syn.neg_score())
    if metric == "Mean":
        pos = mean(posi)
        neg = mean(negi)
    else:
        pos = max(posi)
        neg = max(negi)
    return pos, neg

get_pos_neg_score('fast','Mean')

##############################################################################################
#using NLTK instead of training corpus to build the classifier posScore(sent) ? negScore(sent)

pred = []
actual = []
for line, label in testset:
    pos_rev = neg_rev = 0 
    for word in wt(line):
        pos, neg = get_pos_neg_score(word, "Mean")
        pos_rev+=pos
        neg_rev+=neg
    if pos_rev>neg_rev:
        lab=1
    else:
        lab=-1
    pred.append(lab)
    actual.append(label)
    
actuals = pd.Series(actual)
predicted = pd.Series(pred)
print (actuals)
print (predicted)

# Confusion Matrix
cm1=pd.crosstab(actuals, predicted, rownames=['Actuals'], colnames=['Predicted'], margins=True)
cm1

#precision score and recall scores
from sklearn.metrics import precision_score, recall_score

#Accuracy is lower than the first lexicon classifier 79% Why?
mat1 = cm1.as_matrix()
accuracy = float(mat1[0,0]+mat1[1,1])/mat1[2,2]
print('Accuracy: {0:0.3f}'.format(accuracy))

precision = precision_score(actuals, predicted)
print('Precision score: {0:0.3f}'.format(precision))
recall = recall_score(actuals, predicted)
print('Recall score: {0:0.3f}'.format(recall))

#This workshop is based on some simple Lexicon classifiers. 
#Can you explain the pros and cons of this simple method now?


