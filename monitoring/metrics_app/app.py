#!/usr/bin/env python3

"""
This is a demo service for Evidently metrics integration with Prometheus and Grafana.

Read `README.md` for proper setup and installation.

The service gets a reference dataset from reference.csv file and process current data with HTTP API.

Metrics calculation results are available with `GET /metrics` HTTP method in Prometheus compatible format.
"""
import datetime
import hashlib
import logging
import os
from typing import Dict
from typing import List
from typing import Optional

import dataclasses
import flask
import pandas as pd
import prometheus_client
import yaml
from flask import Flask
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from evidently.model_monitoring import DataDriftMonitor
from evidently.model_monitoring import ModelMonitoring
from evidently.model_monitoring import NumTargetDriftMonitor
from evidently.model_monitoring import RegressionPerformanceMonitor
from evidently.model_monitoring import ClassificationPerformanceMonitor
from evidently.model_monitoring import CatTargetDriftMonitor
from evidently.pipeline.column_mapping import ColumnMapping
from evidently.runner.loader import DataLoader
from evidently.runner.loader import DataOptions
from evidently.options.data_drift import DataDriftOptions

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=[logging.StreamHandler()]
)

# Add prometheus wsgi middleware to route /metrics requests
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {"/metrics": prometheus_client.make_wsgi_app()})


@dataclasses.dataclass
class MonitoringServiceOptions:
    datasets_path: str
    window_size: int
    calculation_period_sec: int


@dataclasses.dataclass
class LoadedDataset:
    name: str
    references: pd.DataFrame
    monitors: List[str]
    column_mapping: ColumnMapping


EVIDENTLY_MONITORS_MAPPING = {
    "data_drift": DataDriftMonitor,
    "num_target_drift": NumTargetDriftMonitor,
}


class MonitoringService:
    # names of monitoring datasets
    metric: Dict[str, prometheus_client.Gauge]
    last_run: Optional[datetime.datetime]
    # reference data
    reference: pd.DataFrame
    # current data
    current:  Optional[pd.DataFrame]
    # monitoring objects
    monitoring: ModelMonitoring
    calculation_period_sec: float = 15
    window_size: int

    def __init__(self, dataset: LoadedDataset, window_size: int):
        self.reference = dataset.references
        self.current = None
        self.dataset_name = dataset.name
        self.column_mapping = {}
        self.window_size = window_size
        options = DataDriftOptions(feature_stattest_func="ks")
        self.monitoring = ModelMonitoring(
            monitors=[EVIDENTLY_MONITORS_MAPPING[k]() for k in dataset.monitors], options=[options]
        )
        self.column_mapping = dataset.column_mapping

        self.metrics = {}
        self.next_run_time = None
        self.hash = hashlib.sha256(pd.util.hash_pandas_object(self.reference).values).hexdigest()
        self.hash_metric = prometheus_client.Gauge("evidently:reference_hash", "", labelnames=["hash"])

    def iterate(self,  new_rows: pd.DataFrame):
        """Add data to current dataset for specified dataset"""
        window_size = self.window_size

        if self.current is not None:
            current_data = self.current.append(new_rows, ignore_index=True)

        else:
            current_data = new_rows

        current_size = current_data.shape[0]

        if current_size > self.window_size:
            # cut current_size by window size value
            current_data.drop(index=list(range(current_size - self.window_size)), inplace=True)
            current_data.reset_index(drop=True, inplace=True)

        self.current = current_data

        if current_size < window_size:
            logging.info(f"Not enough data for measurement: {current_size} of {window_size}." f" Waiting more data")
            return

        next_run_time = self.next_run_time

        if next_run_time is not None and next_run_time > datetime.datetime.now():
            logging.info("Next run for dataset at %s", next_run_time)
            return

        self.next_run_time = datetime.datetime.now() + datetime.timedelta(
            seconds=self.calculation_period_sec
        )
        self.monitoring.execute(
            self.reference, current_data, self.column_mapping
        )
        self.hash_metric.labels(hash=self.hash).set(1)

        for metric, value, labels in self.monitoring.metrics():
            metric_key = f"evidently:{metric.name}"
            found = self.metrics.get(metric_key)

            if not labels:
                labels = {}

            labels["dataset_name"] = self.dataset_name
            if isinstance(value, str):
                continue

            if found is None:
                found = prometheus_client.Gauge(metric_key, "", list(sorted(labels.keys())))
                self.metrics[metric_key] = found

            try:
                found.labels(**labels).set(value)

            except ValueError as error:
                # ignore errors sending other metrics
                logging.error("Value error for metric %s, error: ", metric_key, error)


SERVICE: Optional[MonitoringService] = None


@app.before_first_request
def configure_service():
    # pylint: disable=global-statement
    global SERVICE
    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

    with open(config_file_path, "rb") as config_file:
        config = yaml.safe_load(config_file)

    options = MonitoringServiceOptions(**config["service"])
    datasets_path = os.path.abspath(options.datasets_path)
    loader = DataLoader()
    
    reference_path = os.path.join(datasets_path,  "train.csv")

    dataset_config = config["dataset"]
    reference_data = loader.load(
        reference_path,
        DataOptions(
            date_column=dataset_config.get("date_column", None),
            separator=dataset_config["data_format"]["separator"],
            header=dataset_config["data_format"]["header"],
        ),
    )
    dataset = LoadedDataset(
        name=dataset_config["name"],
        references=reference_data,
        monitors=dataset_config["monitors"],
        column_mapping=ColumnMapping(**dataset_config["column_mapping"]),
    )
    logging.info("Reference is loaded for dataset: %s rows",len(reference_data))

    SERVICE = MonitoringService(dataset=dataset, window_size=options.window_size)


@app.route("/iterate", methods=["POST"])
def iterate():
    item = flask.request.json

    global SERVICE
    if SERVICE is None:
        return "Internal Server Error: service not found", 500

    SERVICE.iterate(new_rows=pd.DataFrame.from_dict(item))
    return "ok"


if __name__ == "__main__":
    app.run(debug=True)
