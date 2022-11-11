import joblib
import pandas as pd

from . import config
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, f1_score
import sys


def train():

    regressor = RandomForestRegressor()
    classifier = RandomForestClassifier()
    df = pd.read_csv(config.URL, delimiter=';')
    df.columns = [x.replace(" ", "_") for x in df.columns]
    features = list(df.columns)
    print(features)
    features.remove(config.TARGET)
    print(features)
    train, prod = train_test_split(
        df,
        test_size=0.2,
        random_state=config.SEED_SPLIT,
    )
    train, test = train_test_split(
        train,
        test_size=0.1,
        random_state=config.SEED_SPLIT,
    )

    regressor.fit(train[features], train[config.TARGET])
    classifier.fit(train[features], train[config.TARGET])

    preds = regressor.predict(test[features])
    mse = mean_squared_error(test[config.TARGET], preds)
    print(f"MSE of the regression model is {mse}")

    preds = classifier.predict(test[features])
    mse = f1_score(test[config.TARGET], preds, average='weighted')
    print(f"F1 of the classification model is {mse}")

    filename = f"{config.REG_MODEL_NAME}"
    print(f"Regression Model stored in models as {filename}")
    joblib.dump(regressor, filename)

    filename = f"{config.REG_MODEL_NAME}"
    print(f"ClassificationModel stored in models as {filename}")
    joblib.dump(classifier, filename)

    train['reg_prediction'] = regressor.predict(train[features])
    prod['reg_prediction'] = regressor.predict(prod[features])
    test['reg_prediction'] = regressor.predict(test[features])

    train['class_prediction'] = classifier.predict(train[features])
    prod['class_prediction'] = classifier.predict(prod[features])
    test['class_prediction'] = classifier.predict(test[features])

    train.to_csv(config.DATA_DIR + "/train.csv", index=False)
    prod.to_csv(config.DATA_DIR + "/prod.csv", index=False )
    test.to_csv(config.DATA_DIR + "/test.csv", index=False )



if __name__ == "__main__":
    train()
