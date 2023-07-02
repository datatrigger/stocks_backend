from __future__ import annotations
from datetime import date, timedelta
from pandas import bdate_range
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from itertools import repeat
import logging
import asyncio
from httpx import AsyncClient

def get_business_days(window: int) -> list[str]:
    """Return the last `window` business days, up to yesterday"""
    yesterday = date.today() - timedelta(days = 1)
    trading_dates = CustomBusinessDay(calendar=USFederalHolidayCalendar())
    days = bdate_range(end = yesterday, periods = window, freq = trading_dates)
    return days.strftime("%Y-%m-%d").to_list()

class HTTPError(Exception):
    pass

async def fetch_price(ticker: str, day: str, client: AsyncClient, api_key: str) -> tuple[str, str, float]:
    """Fetch the closing price for a given ticker/day"""
    payload = f"https://api.polygon.io/v1/open-close/{ticker}/{day}?adjusted=true&apiKey={api_key}"
    try:
        response = await client.get(payload)
        if response.status_code != 200:
            raise HTTPError
        price = float(response.json()["close"])
    except HTTPError as error:
        logging.exception(msg = f"The following HTTP request failed with status code {response.status_code}: {payload}")
        raise error
    except Exception as error:
        logging.exception(msg = "An error occured!")
        raise error    
    return ticker, day, price
    
def get_prices(tickers: list[str], days: list[str], api_key: str) -> list[tuple[str, str, float]]:
    """Wrapper to run all HTTP requests asyncronously"""

    n_days = len(days)
    days = days*len(tickers)
    tickers = (ticker for ticker in tickers for _ in range(n_days))

    async def fetch_all_prices():
        """Fetch the closing prices for all tickers/days"""
        async with AsyncClient() as client:
            return await asyncio.gather(
                *map(fetch_price, tickers, days, repeat(client), repeat(api_key),)
            )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(fetch_all_prices())