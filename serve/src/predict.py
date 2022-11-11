import joblib
from sklearn.pipeline import Pipeline
from pydantic import BaseModel
from fastapi import FastAPI, Depends
import pandas as pd

from . import config
import logging
import json
import sys
import requests
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(name)s:%(message)s")

stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(f"{config.LOG_DIR}/api.log")

stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)


class PredictionInput(BaseModel):
    fixed_acidity: float
    volatile_acidity: float
    citric_acid: float
    residual_sugar: float
    chlorides: float
    free_sulfur_dioxide: float
    total_sulfur_dioxide: float
    density: float
    pH: float
    sulphates: float
    alcohol: float


class PredictionOutput(BaseModel):
    prediction: int


class WineModel:
    prod_model: Pipeline

    def load_model(self):
        """Loads the model"""
        self.prod_model = joblib.load(config.REG_MODEL_NAME)
        logger.info("Model loaded")

    def predict(self, input: PredictionInput) -> PredictionOutput:
        """Runs a prediction"""
        # LOG Aqui INFO
        df = pd.DataFrame([input.dict()])
        if not self.prod_model:
            raise RuntimeError("Model is not loaded")
        prediction = self.prod_model.predict(df)[0]
        results = {
            "input_raw": input.dict(),
            "prediction": str(prediction),
        }
        data = input.dict()
        data['reg_prediction'] = prediction
        data['quality'] = 1
        logger.info(data)
        send_data_to_evidently(data)
        logger.info(f"Prediction:{json.dumps(results)}")
        return PredictionOutput(prediction=prediction)


app = FastAPI()
titanic_model = WineModel()


@app.post("/prediction")
async def prediction(
    output: PredictionOutput = Depends(titanic_model.predict),
) -> PredictionOutput:

    return output


@app.post("/")
async def root():
    return "Hello World"


@app.on_event("startup")
async def startup():
    # Possible Log: Try and Except
    titanic_model.load_model()

# the encoder helps to convert NumPy types in source data to JSON-compatible types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.void):
            return None

        if isinstance(obj, (np.generic, np.bool_)):
            return obj.item()

        return obj.tolist() if isinstance(obj, np.ndarray) else obj

def send_data_to_evidently(data):
    try:
        response = requests.post(
            "http://172.20.0.10:8085/iterate",
            data=json.dumps([data], cls=NumpyEncoder),
            headers={"content-type": "application/json"},
        )

        if response.status_code == 200:
            print("Success.")

        else:
            print(
                f"Got an error code {response.status_code} for the data chunk. "
                f"Reason: {response.reason}, error text: {response.text}"
            )
    except requests.exceptions.ConnectionError as error:
        print(f"Cannot reach a metrics application, error: {error}, data: {data}")