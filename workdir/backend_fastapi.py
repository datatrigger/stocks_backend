from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from dataclasses import dataclass, field
import utils

api_key = os.environ.get("API_KEY") # Fetched from GCP Secrets

@dataclass()
class Stocks:
    window: int
    tickers: list[str]
    days: list[str] = field(init = False)
    prices: list[tuple[str, str, float]] = field(init = False)
    # Chart data
    colors: list[str]
    fill: bool
    chart_payload: dict = field(init = False)

    def __post_init__(self: Stocks) -> None:
        try:
            # Example of validation
            if len(self.colors) != len(self.tickers):
                raise ValueError("Numbers of tickers and colors do not match.")
            self.days = utils.get_business_days(self.window)
            self.prices = utils.get_prices(self.tickers, self.days, api_key)
            self.chart_payload = self.get_chart_payload()
        except Exception as error:
            logging.exception(msg = "An error occured!") # Logs full stack trace
            raise error

    def get_chart_payload(self: Stocks) -> dict:
        body = {}
        body["labels"] = self.days
        datasets = []
        for i, ticker in enumerate(self.tickers):
            dataset = {}
            prices = [datapoint[2] for datapoint in self.prices if datapoint[0] == ticker]
            dataset["data"] = [round(100 * price / prices[0], 3) for price in prices]
            dataset["label"] = ticker
            dataset["borderColor"] = self.colors[i]
            dataset["fill"] = self.fill
            datasets.append(dataset)
        body["datasets"] = datasets
        return body


app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get('/')
def home() -> dict:
    return {'Home': 'Welcome to this stocks API'}

@app.get('/data') # Chart component's endpoint
def data() -> dict:
    stocks = Stocks(
        tickers = ["GOOG", "AMZN", "MSFT"],
        window = 10,
        colors = ["#8e5ea2", "#3cba9f", "#e8c3b9"],
        fill = False
    )
    return stocks.chart_payload