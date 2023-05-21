from fastapi import FastAPI
import requests
import logging
import os
import pandas as pd
from datetime import date, timedelta
from math import sqrt

api_key = os.environ.get("API_KEY") # Fetched from GCP Secrets, by GCP Cloud Run
tickers = {"Google": "GOOG", "Amazon": "AMZN", "Microsoft": "MSFT"}
bdays_window = 10
# Charts params
colors = {"Google": "#8e5ea2", "Amazon": "#3cba9f", "Microsoft": "#e8c3b9"}
fill = False

def previous_bdays(window: int = bdays_window - 1) -> list[str]:
    """Return the last `window` business days, up to yesterday (at most)"""
    yesterday = date.today() - timedelta(days = 1)
    previous_bdays = pd.bdate_range(end = yesterday, periods = window).strftime("%Y-%m-%d")
    return previous_bdays.tolist()

def current_price(company: str) -> float | None:
    """Fetch the last know trading price for the given `company`"""
    try:
        ticker = tickers[company]
    except KeyError:
        logging.error("Unregistered company. Unable to fetch current price.")
        return
    query = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={api_key}"

    try:
        response = requests.get(query)
        response.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        logging.error("HTTP Error:",errh)
    except requests.exceptions.ConnectionError as errc:
        logging.error("Error Connecting:",errc)
    except requests.exceptions.Timeout as errt:
        logging.error("Timeout Error:",errt)
    except requests.exceptions.RequestException as err:
        logging.error("Unknown error:",err)

    price = response.json()["results"]["p"]
    return float(price)

def history(company: str) -> list[float | None]:
    """
    Fetch history of stock prices for passed `company` over the last `bdays_window` business days
    Time window is a global variable for now, as the user cannot set in the frontend.
    This part makes the application slow (20s load-time) because there is 1 API call/(day*company)
    Next step would be to have history available in a remote bucket or database
    OR to make concurrent requests. 
    """
    try:
        ticker = tickers[company]
    except KeyError:
        logging.error("Unregistered company. Unable to fetch history.")
        return []
    
    prices = []
    for day in previous_bdays():
        query = f"https://api.polygon.io/v1/open-close/{ticker}/{day}?adjusted=true&apiKey={api_key}"
        try:
            response = requests.get(query)
            response.raise_for_status()
        except requests.exceptions.HTTPError as errh:
            logging.error("HTTP Error:",errh)
        except requests.exceptions.ConnectionError as errc:
            logging.error("Error Connecting:",errc)
        except requests.exceptions.Timeout as errt:
            logging.error("Timeout Error:",errt)
        except requests.exceptions.RequestException as err:
            logging.error("Unknown error:",err)
    
        closing_price = float(response.json()["close"])
        prices.append(closing_price)

    return prices

def full_data(dataframe: bool = False) -> dict[str: list[float]] | pd.DataFrame:
    """
    Assemble history + current price in 1 dataset
    Return a dictionary or a pandas dataframe
    """
    dates = previous_bdays() + [date.today().strftime("%Y-%m-%d")]
    prices = {}
    for company in tickers:
        prices[company] = history(company) + [current_price(company)]
    if dataframe:
        return pd.DataFrame(index = dates, data = prices)
    return {"dates": dates} | prices

def body_chart(raw_data: dict[str: list[float]]) -> dict:
    """Format data to be consumed by the frontend chart component"""
    body = {}
    body["labels"] = raw_data["dates"]
    datasets = []
    for company in tickers:
        dataset = {}
        dataset["data"] = [100 * price / raw_data[company][0] for price in raw_data[company]]
        dataset["label"] = company
        dataset["borderColor"] = colors[company]
        dataset["fill"] = fill
        datasets.append(dataset)
    body["datasets"] = datasets
    return body

def compute_metrics() -> pd.DataFrame:
    """Compute requested metrics over full data (current + history)"""
    prices = full_data(dataframe = True)
    returns = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]
    returns_daily = (prices - prices.shift(1)) / prices.shift(1)
    df_metrics = pd.DataFrame({
        "Return": returns,
        "Annualized Return": returns.apply(func = lambda r: (1 + r) ** (365 / bdays_window) - 1),
        "Annualized Volatility": returns_daily.std() * sqrt(261)
    })
    return df_metrics

def stringify_row(row: list[str]) -> str:
    """
    Convert a row of data in a string.
    The original plan was to pass fixed-width strings to the frontend
    But Vue automatically trims whitespaces
    """
    return '| '.join(map(lambda s: '{:<20}'.format(s), row))

def format_row(company: str, df_metrics: pd.DataFrame) -> list[str]:
    """Format percentages for more readability"""
    return [company] + [str(round(100 * x, 2)) + " %" for x in df_metrics.loc[company]]

def body_metrics(df_metrics: pd.DataFrame) -> dict[str: list[str]]:
    rows = [stringify_row(["Company"] + list(df_metrics.columns))]
    for company in tickers:
        rows.append(stringify_row(format_row(company, df_metrics)))
    return {"metrics": rows}

# CORS: needs refinement, necessary for the frontend to connect
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
def home() -> dict:
    return {'Home': 'Welcome to this stocks API'}

# Chart component's endpoint
@app.get('/data')
def data() -> dict:
    return body_chart(full_data())

# Table of metrics component's endpoint
@app.get('/metrics')
def metrics() -> dict:
    return body_metrics(compute_metrics())