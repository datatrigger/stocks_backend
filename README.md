# Stocks

* [Single-page application](https://stocks.vlgdata.io/)
* [Vue Frontend](https://github.com/datatrigger/stocks_frontend)
* Backend: hosted here

# Presentation

This application shows live data about trading stock prices for Amazon, Google and Microsoft:
* Line chart: value of the stock over the past 9 business days (closing price) + current value (15-min old at most during market hours)
* Metrics:
    * Cumulative Return: $R_c = \frac{P_{end} - P_{start}}{P_{start}}$
    * Annualized return: $R_a = (1 + R_c)^{\frac{365}{n}} - 1$, $n$ is the length of window in days
    * Annualized Volatility: $\sqrt{261} \sigma_r$, with $\sigma_r$ the standard deviation of the daily returns

The time window has been chosen to be short: half a trading month. In this context, the annualized metrics do not make as much sense, but the live data and its impact are more visible.

# Architecture and implementation

## Frontend

The frontend is implement with JavaScript framework Vue.js (version 3, Component API). It is built with Vite and deployed directly from the repository on Netlify, in a CI/CD fashion.

## Backend

The backend is implemented with Python and FastAPI. It has been dockerized and the image is pushed on Google's container registry (Artifact). From there,Google Cloud Run deploys it. Also, continuous integration has been configured so that Cloud Run triggers the build of the image at each push on the source repo.

The data is fetched using the Polygon API and the key is stored with Google Secrets. At runtime, Cloud Run fetches the key and injects it in the container as an environment variable.

# Future plans to make this app better

* Learn JavaScript and Vue
    * Async requests and promises are not properly handled
    * Data should be updated without user refreshing: need to investigate `setInterval()`
    * The metrics are there but no actual table component was implemented in time
* Implement unit tests and integrations tests
* Implement error handling, especially in async HTTP requests
* Use Google Cloud Functions or AWS Lambda to store historical data on a daily basis on a remote service (bucket, database)
    * Avoid re-fetching historical data at every update
    * Likely to decrease loading time
* Features:
    * Let user choose time window
    * Let user select among a set of companies/tickers
