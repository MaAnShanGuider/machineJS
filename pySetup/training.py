import sys
import csv
import math
import os
import time
import json
import joblib
from sklearn.cross_validation import train_test_split
from sklearn.grid_search import GridSearchCV
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sendMessages import printParent
from sendMessages import messageParent
# based on the arguments passed in, load a new module
    # that module will just be the new classifier. 
    



X = []
y = []

y_file_name = json.loads(sys.argv[3])['y_train']
X_file_name = json.loads(sys.argv[3])['X_train']

with open(X_file_name, 'rU') as openInputFile:
    inputRows = csv.reader(openInputFile)
    for row in inputRows:
        # for value in row:
        #     if value == 'nan'

        X.append(row)
        

with open(y_file_name, 'rU') as openOutputFile:
    outputRows = csv.reader(openOutputFile)
    for row in outputRows:
        try:
            row[0] = float(row[0])
        except:
            row[0] = row[0]
        y.append(row[0])

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.5, random_state=0)
globalArgs = json.loads(sys.argv[2])

# if we're developing, train on only 1% of the dataset.
extendedTraining=True
for key in globalArgs:
    if key in( 'devKaggle', 'dev'): 
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.99, random_state=0)
        extendedTraining = False

# TODO: At this point, load in the module for training each classifier specifically. 
# Everything above this line is shared across classifiers
# Most things below this line are specific to each classifier

'''
determine which parameters we want to mess with
    https://www.kaggle.com/forums/f/15/kaggle-forum/t/4092/how-to-tune-rf-parameters-in-practice
    A. M-Try (number of features it tries at each decision point in a tree). Starts at square root of features available, but tweak it up and down by a few (probably no more than 3 in each direction; it seems even 1 or 2 is enough)
    B. Number of folds for cross-validation: 10 is what most people use, but more gives you better accuracy (likely at the cost of compute time). again, returns are pretty rapidly diminishing. 
    C. platt scaling of the results to increase overall accuracy at the cost of outliers (which sounds perfect for an ensemble)
    D. preprocessing the data might help- FUTURE
    E. Principle Component Analysis to decrease dependence between features
    F. Number of trees
    G. Possibly ensemble different random forests together. this is where the creative ensembling comes into play!
    H. Splitting criteria
    I. AdaBoost
    J. Can bump up nodesize as much as possible to decrease training time (split)
        consider doing this first, finding what node size we finally start decreasing accuracy on, then use that node size for the rest of the testing we do, then possibly bumping it down a bit again at the end. 
            https://www.kaggle.com/c/the-analytics-edge-mit-15-071x/forums/t/7890/node-size-in-random-forest
    K. min_samples_leaf- smaller leaf makes you more prone to capturing noise from the training data. Try for at least 50??
        http://www.analyticsvidhya.com/blog/2015/06/tuning-random-forest-model/
    L. random_state: adds reliability. Would be a good one to split on if ensembling different RFs together. 
    M. oob_score: something about intelligent cross-validation. 
    N. allusions to regularization, or what I think they mean- feature selection. 

'''

# instantiate a new classifier. This part might have to be done individually. 
    # we can probably have a module that is just a dict of names ('randomForest') to their instantiated classifiers
rf = RandomForestClassifier(n_estimators=15, n_jobs=globalArgs['numCPUs'])

# create features that are custom to the size of the input data. 
# this will definitely have to be done individually. 
# i don't see any harm in making each of these into their own file, because aside from the dev check, everything here will be custom to each classifier. 
sqrtNum = int(math.sqrt(len(X[0])))

max_features_to_try = [sqrtNum + x for x in (-2,0,2)]
max_features_to_try.append('log2')
max_features_to_try.append(None)


parameters_to_try = {
    'max_features': max_features_to_try,
    'min_samples_leaf':[1,2,5,25,50,100,150],
    'criterion': ['gini','entropy']
}

for key in globalArgs:
    if key in( 'devKaggle', 'dev'): 
        parameters_to_try.pop('min_samples_leaf', None)
        parameters_to_try.pop('max_features', None)


# here is where we start to do very similar things all over again. everything from here forwards can be generalized. 
printParent('we are about to run a grid search over the following space:')
printParent(parameters_to_try)

gridSearch = GridSearchCV(rf, parameters_to_try, cv=10, n_jobs=globalArgs['numCPUs'])

gridSearch.fit(X_train, y_train)

printParent('we have used grid search to explore the entire parameter space and find the best possible version of a random forest for your particular data set!')

printParent('*********************************************************************************************************')
printParent("this estimator's best prediction is:")
printParent(gridSearch.best_score_)
printParent('*********************************************************************************************************')
printParent("this estimator's best parameters are:")
printParent(gridSearch.best_params_)
printParent('now that we have figured this out, we are going to train a random forest with considerably more trees. more trees means a better fit, but they also take significantly longer to train, so we kept the number of trees relatively low while searching through the parameter space to make sure you were not stuck here until python6 comes out.')

# this part, unfortunately, will probably have to be custom for each one, despite having a fair bit of boilerplate code. 
# actually, no, i think even this part can be mostly generalized. 
    # create a dict with mappings from algo name ('randomForest') to a function that will return a newly instantiated version of that algo (with the proper n_estimators and other custom parameters for that classifier)
    # then we just use a for loop to loop through best_params_ and set each of those as properties on the estimator. 
if extendedTraining:
    bigRF = RandomForestClassifier(n_estimators=1500, n_jobs=globalArgs['numCPUs'])
    bigRF.set_params(criterion=gridSearch.best_params_['criterion'])
    try:
        bigRF.set_params(max_features=gridSearch.best_params_['max_features'])
    except:
        None
        
    try:
        bigRF.set_params(min_samples_leaf=gridSearch.best_params_['min_samples_leaf'])
    except:
        None

    # note: we are testing grid search on 50% of the data (X_train and y_train), but fitting bigRF on the entire dataset (X,y)
    bigRF.fit(X, y)
    printParent('we have trained an even more powerful random forest!')

    bigRFscore = bigRF.score(X, y)
    printParent('the bigger randomForest has a score of')
    printParent(bigRFscore)

    # we will, of course, need to work on our file structure a bit. 
    # and each classifier will have to write to it's own folder there, so we are going to have to be super consistent in our variable naming. 
        # and lets make the classifier names something super unique so it's easy to do a global search and replace for it. maybe 'cl' + algo name, like 'clRandomForest'?
    joblib.dump(bigRF, 'pySetup/bestRF/bestRF.pkl')
else:
    joblib.dump(gridSearch.best_estimator_, 'pySetup/bestRF/bestRF.pkl')
printParent('wrote the best estimator to a file')
