# Stocks

* [Single-page application](https://stocks.vlgdata.io/)
* [Vue Frontend](https://github.com/datatrigger/stocks_frontend)
* Backend: hosted in *this* repo

# Presentation

This application shows live data about trading stock prices for Amazon, Google and Microsoft:
* Line chart: value of the stock over the past 9 business days (closing price) + current value (15-min old at most during market hours)
* Metrics: 

This repository hosts the backend of this [single-page application](https://stocks.vlgdata.io/), displaying live data about 3 Big Tech stocks.
The frontend lives in this [repository](https://github.com/datatrigger/stocks_frontend)

It is implemented with the javascript framework Vue 3 (Component API) and built with Vite.

This frontend is deployed by Netlify from this repo (folder `dist`) with CI/CD.

The backend lives in this [repository](https://github.com/datatrigger/stocks_backend).
