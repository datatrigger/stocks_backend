from fastapi import FastAPI
import requests
import logging
import json
import os
import pandas as pd
from datetime import date, timedelta
from math import sqrt

api_key = os.environ.get("API_KEY")
tickers = {"Google": "GOOG", "Amazon": "AMZN", "Microsoft": "MSFT"}
bdays_window = 10

def previous_bdays(window: list[str] = bdays_window - 1):
    # today = date.today().strftime("%Y-%m-%d")
    yesterday = date.today() - timedelta(days = 1)
    previous_bdays = pd.bdate_range(end = yesterday, periods = window).strftime("%Y-%m-%d")
    return previous_bdays.tolist()# + [today]

def current_price(company: str) -> float | None:
    """"""
    try:
        ticker = tickers[company]
    except KeyError:
        logging.error("Unregistered company. Unable to fetch current price.")
        return
    query = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={api_key}"
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
        query = f"https://api.polygon.io/v1/open-close/{ticker}/{day}?adjusted=true&apiKey={api_key}"
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

def compute_metrics() -> pd.DataFrame:
    prices = full_data(dataframe = True)
    returns = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]
    returns_daily = (prices - prices.shift(1)) / prices.shift(1)
    df_metrics = pd.DataFrame({
        "return": returns,
        "annualized_return": returns.apply(func = lambda r: (1 + r) ** (365 / bdays_window) - 1),
        "annualized_volatility": returns_daily.std() * sqrt(261)
    })
    return df_metrics


app = FastAPI()

@app.get('/')
def home():
    return {'Home': 'Welcome to this stocks API'}

@app.get('/data')
def data():
    return json.dumps(full_data())

@app.get('/metrics')
def metrics():
    return compute_metrics().to_json()