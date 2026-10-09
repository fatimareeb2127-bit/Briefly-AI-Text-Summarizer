# Briefly AI: redesigned website

A responsive, animated Flask website styled to match the supplied Briefly AI reference image. Includes the original local BART summarization path and frequency-based extractive fallback.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies: `pip install -r requirements.txt`
4. Start the app: `python app.py`
5. Open `http://127.0.0.1:5000`.

## Model behavior

The app loads `facebook/bart-large-cnn` from the local cache only. It does not download the model automatically. If the model is unavailable, the extractive fallback selects high-scoring sentences from the source text.

## Files

- `app.py`: Flask routes and summarization logic
- `templates/index.html`: website structure
- `static/css/style.css`: visual design, responsiveness, animations, light theme
- `static/js/script.js`: frontend interactions and API requests
- `requirements.txt`: Python dependencies
