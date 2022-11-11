import os
BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-white.csv"

SEED_SPLIT = 404
SEED_MODEL = 404
CLASS_MODEL_NAME = os.path.realpath(os.path.join(BASE_DIR, "models", "class_model.sav"))
REG_MODEL_NAME = os.path.realpath(os.path.join(BASE_DIR, "models", "reg_model.sav"))
DATA_DIR = os.path.realpath(os.path.join(BASE_DIR, "data"))
TARGET = "quality"
