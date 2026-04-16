# NPTEL Helper

An NPTEL question-practice app that stores progress in browser localStorage and can generate concise Gemini explanations when configured with an API key.

## Local development

1. Install dependencies with `pip install -r requirements.txt`.
2. Set `GEMINI_API_KEY` in your shell or `.env.local` if you want AI explanations.
3. Run `python app.py` and open the local URL printed by Flask.

## Vercel deployment

1. Create a Vercel project from this repository.
2. Add the environment variable `GEMINI_API_KEY` in the Vercel dashboard if you want AI explanations.
3. Deploy the project; Vercel will detect the top-level `app` object in `app.py`.

## Scraper utility

The Playwright scraper is kept separate from the production app. Install its dependencies with `pip install -r requirements-scraper.txt` if you want to use `scraper.py`.