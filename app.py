from __future__ import annotations

import re
from collections import Counter

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MODEL_NAME = "facebook/bart-large-cnn"
_summarizer = None
_model_status = {"mode": "not_loaded", "message": "Model loads on first request."}

try:
    from transformers import pipeline
except Exception:
    pipeline = None


def fallback_summarize(text: str, sentence_limit: int = 3) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return text.strip()

    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "or", "that",
        "the", "their", "this", "to", "was", "were", "will", "with", "you",
        "your", "they", "them", "than", "then", "there", "these", "those",
    }
    word_freq = Counter(
        word.lower()
        for word in re.findall(r"\b[a-zA-Z]+\b", text)
        if len(word) > 2 and word.lower() not in stop_words
    )
    if not word_freq:
        return " ".join(sentences[:sentence_limit])

    scored = []
    for index, sentence in enumerate(sentences):
        words = re.findall(r"\b[a-zA-Z]+\b", sentence.lower())
        score = sum(word_freq.get(word, 0) for word in words)
        scored.append((score, index, sentence))

    chosen = sorted(sorted(scored, key=lambda item: item[0], reverse=True)[:sentence_limit], key=lambda item: item[1])
    summary = " ".join(item[2] for item in chosen).strip()
    return summary or " ".join(sentences[:sentence_limit])


def load_summarizer():
    global _summarizer, _model_status
    if _summarizer is None:
        if pipeline is None:
            _summarizer = {"fallback": True}
            _model_status = {"mode": "offline", "message": "Transformers is unavailable. Extractive fallback is active."}
        else:
            try:
                # Use local_files_only so startup never requires a network download.
                _summarizer = pipeline(
                    "summarization",
                    model=MODEL_NAME,
                    tokenizer=MODEL_NAME,
                    device=-1,
                    local_files_only=True,
                )
                _model_status = {"mode": "bart", "message": "BART model loaded from local cache."}
            except Exception as exc:
                _summarizer = {"fallback": True}
                _model_status = {"mode": "offline", "message": f"Local BART model unavailable. Extractive fallback is active ({type(exc).__name__})."}
    return _summarizer


def summarize_text(text: str, length: str = "medium") -> tuple[str, str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ValueError("Please provide some text to summarize.")

    settings = {
        "short": (60, 15, 2),
        "medium": (130, 30, 3),
        "long": (220, 60, 5),
    }
    max_length, min_length, sentence_limit = settings.get(length, settings["medium"])
    summarizer = load_summarizer()

    if isinstance(summarizer, dict) and summarizer.get("fallback"):
        return fallback_summarize(cleaned, sentence_limit), "offline"

    try:
        # BART's minimum length can exceed a short input. Use fallback for short text.
        if len(cleaned.split()) < 35:
            return fallback_summarize(cleaned, sentence_limit), "offline"
        result = summarizer(cleaned, max_length=max_length, min_length=min_length, do_sample=False)
        _model_status = {"mode": "bart", "message": "Summary generated with BART."}
        return result[0]["summary_text"], "bart"
    except Exception:
        return fallback_summarize(cleaned, sentence_limit), "offline"


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    load_summarizer()
    return jsonify(_model_status)


@app.post("/api/summarize")
def summarize():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    length = data.get("length", "medium")
    if not isinstance(text, str) or not text.strip():
        return jsonify({"error": "Paste or type some text first."}), 400
    if len(text) > 100000:
        return jsonify({"error": "Please keep the input under 100,000 characters."}), 413

    try:
        summary, mode = summarize_text(text, length)
        original_words = len(re.findall(r"\b\w+\b", text))
        summary_words = len(re.findall(r"\b\w+\b", summary))
        compression = round((1 - summary_words / original_words) * 100, 1) if original_words else 0
        return jsonify({
            "summary": summary,
            "mode": mode,
            "original_words": original_words,
            "summary_words": summary_words,
            "compression": max(0, compression),
            "status_message": _model_status["message"],
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "The text could not be summarized. Try a shorter input."}), 500


if __name__ == "__main__":
    app.run(debug=True)
