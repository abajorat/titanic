import os

BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))
REG_MODEL_NAME = os.path.realpath(os.path.join(BASE_DIR, "models", "reg_model.sav"))
LOG_DIR = os.path.realpath(os.path.join(BASE_DIR, "logs"))
