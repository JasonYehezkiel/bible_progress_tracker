# 📖 Bible Progress Tracker

An end-to-end NLP pipeline that automatically tracks Bible reading progress from Indonesian-language WhatsApp group chat exports. Built as a university capstone project.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-FFD21E?logo=huggingface&logoColor=black)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?logo=opensourceinitiative&logoColor=white)

---

## 📑 Table of Contents
- [Overview](#-overview)
- [Features](#-features)  
- [Project Structure](#-project-structure)
- [Models](#-models)
- [Key Components](#-key-components)  
- [Getting Started](#-getting-started)
- [Tech Stack](#-tech-stack)
- [License](#-license)
- [Author](#-author)

## 🗺️ Overview

WhatsApp-based Bible reading communities often track progress manually, which is tedious and inefficient. This system ingest `.txt` chat exports. extracts Bible references using fine-tuned **IndoBERT NER model**, normalizes them against a canonical Bible corpus, checks compliance against a reading schedule, and surfaces insights through a **Streamlit** dashboard backed by **SQLite**

## 🌟 Features
- 📥 **Automated parsing** of WhatsApp .txt chat exports
- 🏷️ **Message classification** — filters progress messages from general chat noise
- 🔍 **Indonesian-language NER** — fine-tuned IndoBERT extracts Bible references from informal text
- ✅ **Compliance tracking** — classifies each member's reading as `ahead`, `on_time`, or `late`
- 📊 **Interactive dashboard** — Streamlit UI for uploading exports and viewing member progress
- 💾 **Persistent storage** — idempotent SQLite-backed pipeline with SQLAlchemy ORM

## 📂 Project Structure

```
app/
├── .streamlit/
│   └── config.toml             # Streamlit theme & server configuration
├── components/
│   ├── members.py              # Member management page
│   ├── progress.py             # Reading progress page
│   └── upload.py               # Chat export upload page
└── main.py                     # Streamlit entry point
└── state.py                    # Streamlit session state initialization & management
│
src/
├── bible/
│   ├── normalization/
│   │   ├── normalizer.py       # Raw book names → canonical book names
│   │   ├── resolver.py         # BookResolver: exact + fuzzy strategy pattern
│   │   └── validator.py        # Book range validation
│   └── data.py                 # Canon definitions, book_lookup, sorted_books
│
├── compliance/
│   ├── checker.py              # Compliance logic (late/on_time/ahead)
│   └── schedule.py             # Reading schedule definitions
│
├── core/
│   ├── config/
│   │   └── settings.py         # App-wide settings (paths, thresholds, flags)
│   └── logger.py               # Centralized logging
│
├── extraction/
│   ├── indobert.py             # Fine-tuned IndoBERT NER model wrapper
│   ├── crf.py                  # CRF-based extractor (with Word2Vec features)
│   ├── rule_based.py           # Regex baseline extractor
│   └── ner_parser.py           # spans → structured data converter
│
├── ingestion/
│   ├── whatsapp.py             # WhatsApp .txt export parser
│   └── text_cleaner.py         # Unicode normalization, text cleaning etc.
│
├── sessions/
│   ├── db.py                   # SQLAlchemy engine & session factory
│   └── repository.py           # CRUD repository layer
│
├── classification.py           # Message-level reference classifier
├── pipelines.py                # BibleProgressPipeline orchestrator
└── services.py                 # Service-layer business logic
```

---
## 🧠 Models

| Tasks | Models | Baseline |
|---|---------|-------------|
| Classification | TF-IDF + Random Forest | - |
| Entity Extraction | IndoBERT | Word2Vec + CRF and Regex Baseline |
| Normalization | Gazetteer + fuzzy matching | Gazetteer only |

---

### 📦 Pretrained Weights

The fine-tuned IndoBERT NER model is available on Hugging Face:

[![HuggingFace](https://img.shields.io/badge/🤗%20HuggingFace-TidBitRetro%2Findobert--bible--ner-FFD21E)](https://huggingface.co/TidBitRetro/indobert-bible-ner)

Download and place it in the path configured in your `.env` file, or load it directly:
```python
from transformers import AutoTokenizer, AutoModelForTokenClassification

model = AutoModelForTokenClassification.from_pretrained("TidBitRetro/indobert-bible-ner")
tokenizer = AutoTokenizer.from_pretrained("TidBitRetro/indobert-bible-ner")
```

---
## ⚙️ Key Components

**Ingestion**

`WhatsAppParser` reads exported `.txt` files and produces structured pandas `DataFrame` with 3 columns, sender, timestamp, and message.

**Classification**  

`MessageClassifier` classifies each message as either a **progress** or **non-progress** message using a TF-IDF vectorizer paired with a Random Forest classifier, filtering out irrelevant chat noise before the extraction step. 

**Extraction**  

The fine-tuned IndoBERT model tags tokens with BIO labels.
`ner_parser` converts the raw tagged spans into structured data consisting of (`book_start`, `start_chapter`, `book_end`, `end_chapter`).

**Normalization**

`BookResolver` uses a Strategy pattern: exact match first, `FuzzyBookMatcher` as fallback. The fuzzy matcher runs a WRatio broad sweep then re-ranks candidates with a weighted ensemble of Jaro-Winkler and character bigram Jaccard.

**Validation**

`BibleReferenceValidator` validates if the chapter ranges are valid, before persisting it to DB.

**Compliance**

`ComplaianceChecker` compares extracted references against the active reading schedule and classifies each as `ahead`, `on_time`, `late`. 

**Persistence**

`repository` exposes a thin CRUD layer over SQLAlchemy. 

---

# 🚀 Getting Started

**Prerequisites**
- Python 3.10+
- (Optional) CUDA-capable GPU for IndoBERT inference.

**Installation**
```
git clone https://github.com/JasonYehezkiel/bible_progress_tracker.git
cd bible_progress_tracker

python -m venv .venv
.venv\Scripts\activate # MacOS/Linux: source .venv/bin/activate

pip install -r requirements.txt
```

**Configuration**
```
cp .env.example .env
```
Edit `.env` to set the model checkpoint path, database path, and other paths.

**Running**
**Streamlit Dashboard**
```
streamlit run app/main.py
```

**Testing**
```
pytest tests/ -v
```

Test coverage includes:
- Unit Testing — individual components (classifier, extractor, normalizer, services, whatsapp_parser)
- Integration Testing — database and repository interaction testing (db, repository).

## 🛠️ Tech Stack

| Layer | Technology  |
|---|---------|
| Classifier | TF-IDF + Random Forest (`scikit-learn`) |
| NER Model | `transfomers`· IndoBERT (`indolem/indobert-base-uncased`) |
| Fuzzy matching | `rapidfuzz`|
| ORM/DB | SQLAlchemy · SQLite3 |
| Frontend | Streamlit |
| Testing | pytest |

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 👤  Authors:

Name: Jason Yehezkiel Wijaya