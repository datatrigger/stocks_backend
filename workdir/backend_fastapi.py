from fastapi import FastAPI
import logging
import os
import pandas as pd
from datetime import date, timedelta
from math import sqrt
import asyncio
from itertools import repeat, product
import httpx

api_key = os.environ.get("API_KEY") # Fetched from GCP Secrets, by GCP Cloud Run
tickers = {"Google": "GOOG", "Amazon": "AMZN", "Microsoft": "MSFT"}
window = 10
# Charts params
colors = {"Google": "#8e5ea2", "Amazon": "#3cba9f", "Microsoft": "#e8c3b9"}
fill = False

def previous_bdays() -> list[str]:
    """Return the last `window` business days, up to yesterday (at most)"""
    bdays_window = window - 1
    today = date.today().strftime("%Y-%m-%d")
    yesterday = date.today() - timedelta(days = 1)
    previous_bdays = pd.bdate_range(end = yesterday, periods = bdays_window).strftime("%Y-%m-%d")
    return previous_bdays.tolist() + [today]

async def fetch_price(company_day: tuple[str, str], client: httpx.AsyncClient) -> None:
    """Fetch the closing price on a previous business day, or today's current price"""
    company, day = company_day
    today = date.today().strftime("%Y-%m-%d")
    # Error handling needed
    if day == today or day == "2023-05-29":
        response = await client.get(f"https://api.polygon.io/v2/last/trade/{tickers[company]}?apiKey={api_key}")
        price = response.json()["results"]["p"]
    else:
        response = await client.get(f"https://api.polygon.io/v1/open-close/{tickers[company]}/{day}?adjusted=true&apiKey={api_key}")
        price = float(response.json()["close"])
    return company, day, price


async def fetch_all_prices():
    """Fetching the prices for all (company, day)"""
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(
            *map(fetch_price, product(tickers.keys(), previous_bdays()), repeat(client),)
        )

def build_dataset(dataframe: bool = False) -> dict[str: list[float]] | pd.DataFrame:
    """Organize and order data fetched through asynchronous calls"""    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    company_day_price = loop.run_until_complete(fetch_all_prices())
    data_dict = {}
    for datapoint in company_day_price:
        data_dict[(datapoint[0], datapoint[1])] = datapoint[2]
    days = previous_bdays()
    prices = {}
    for company in tickers:
            prices[company] = [data_dict[company, day] for day in days]
    if dataframe:
        return pd.DataFrame(index = days, data = prices)
    return {"dates": days} | prices

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
    prices = build_dataset(dataframe = True)
    returns = (prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0]
    returns_daily = (prices - prices.shift(1)) / prices.shift(1)
    df_metrics = pd.DataFrame({
        "Return": returns,
        "Annualized Return": returns.apply(func = lambda r: (1 + r) ** (365 / window) - 1),
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
    """Format data to be consumed by the frontend Table component"""
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
    return body_chart(build_dataset())

# Table of metrics component's endpoint
@app.get('/metrics')
def metrics() -> dict:
    return body_metrics(compute_metrics())