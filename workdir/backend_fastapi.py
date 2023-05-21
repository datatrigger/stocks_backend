from fastapi import FastAPI
import requests
import logging
import os
import pandas as pd
from datetime import date, timedelta
from math import sqrt

api_key = os.environ.get("API_KEY")
tickers = {"Google": "GOOG", "Amazon": "AMZN", "Microsoft": "MSFT"}
bdays_window = 10
# Charts
colors = {"Google": "#8e5ea2", "Amazon": "#3cba9f", "Microsoft": "#e8c3b9"}
fill = False

def previous_bdays(window: list[str] = bdays_window - 1):
    yesterday = date.today() - timedelta(days = 1)
    previous_bdays = pd.bdate_range(end = yesterday, periods = window).strftime("%Y-%m-%d")
    return previous_bdays.tolist()

def current_price(company: str) -> float | None:
    """"""
    try:
        ticker = tickers[company]
    except KeyError:
        logging.error("Unregistered company. Unable to fetch current price.")
        return
    query = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={api_key}" # Error handling needed
    response = requests.get(query) # Error handling
    price = response.json()["results"]["p"]
    return float(price)

def history(company: str) -> list[float | None]:
    """"""
    try:
        ticker = tickers[company]
    except KeyError:
        logging.error("Unregistered company. Unable to fetch history.")
        return []
    prices = []
    for day in previous_bdays():
        query = f"https://api.polygon.io/v1/open-close/{ticker}/{day}?adjusted=true&apiKey={api_key}" # Error handling
        response = requests.get(query)
        closing_price = float(response.json()["close"])
        prices.append(closing_price)
    return prices

def full_data(dataframe: bool = False) -> pd.DataFrame:
    dates = previous_bdays() + [date.today().strftime("%Y-%m-%d")]
    prices = {}
    for company in tickers:
        prices[company] = history(company) + [current_price(company)]
    if dataframe:
        return pd.DataFrame(index = dates, data = prices)
    return {"dates": dates} | prices

def body_chart(raw_data):
    body = {}
    body["labels"] = raw_data["dates"]
    datasets = []
    for company in tickers:
        dataset = {}
        dataset["data"] = raw_data[company]
        dataset["label"] = company
        dataset["borderColor"] = colors[company]
        dataset["fill"] = fill
        datasets.append(dataset)
    body["datasets"] = datasets
    return body

def compute_metrics() -> pd.DataFrame:
    prices = full_data(dataframe = True)
    returns = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]
    returns_daily = (prices - prices.shift(1)) / prices.shift(1)
    df_metrics = pd.DataFrame({
        "Return": returns,
        "Annualized Return": returns.apply(func = lambda r: (1 + r) ** (365 / bdays_window) - 1),
        "Annualized Volatility": returns_daily.std() * sqrt(261)
    })
    return df_metrics

def stringify_row(row):
    return ''.join(map(lambda s: '{:<20}'.format(s), row))

def formatted_row(company, df_metrics):
    return [company] + [str(round(100 * x, 2)) + " %" for x in df_metrics.loc[company]]

def body_metrics(df_metrics):
    rows = [stringify_row(["Company"] + list(df_metrics.columns))]
    for company in tickers:
        rows.append(stringify_row(formatted_row(company, df_metrics)))
    return {"metrics": rows}

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def home():
    return {'Home': 'Welcome to this stocks API'}

@app.get('/data')
def data():
    return body_chart(full_data())

@app.get('/metrics')
def metrics():
    return body_metrics(compute_metrics())