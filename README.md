# The frequency of the word should in Respekt

I started thinking that the magazine I read started preaching. I thought that I will check if it's the case by analyzing the frequency of the word "should" (měl by in Czech). 


This repo contains
- `scraper.py` - Scrapes articles from Respekt web. Uses curl command exported from firefox dev mode to get all headers representing authenticated user (you must have a subscription)
- `experiment.ipynb` - notebook exploring the data (and showing the histogram of "should" per year)
- `pyproject.toml` - project dependencies for `poetry`
