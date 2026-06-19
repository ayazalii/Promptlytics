# 📊 Promptlytics — Natural Language to Dashboards

> **Promptlytics** converts plain-English business questions into interactive Plotly dashboards — no SQL knowledge required.  
> Built as a minor project at JECRC University (B.Tech CSE — AI/ML), under the supervision of Mr. Mohd. Talib (Xebia).

---

## ✨ Features

| Feature | Detail |
|---|---|
| Natural Language Input | Type a plain-English question about sales data |
| Rule-based NLP Engine | Tokenization → Intent Classification → SQL Generation (no API key needed) |
| Optional OpenAI Path | Provide an `sk-...` key to use GPT-3.5-turbo for SQL generation |
| Smart Chart Selection | Auto-picks Line / Pie / Bar / Indicator / Table based on query type |
| 4-tab Output | Visualization · Insights · Generated SQL · Raw Data |
| SQLite Backend | Lightweight, zero-config local database, auto-seeded on first run |

---

## 🖥️ Screenshots

| Monthly Revenue Trend (Line) | Quantity by Product (Pie) | Region Sales (Bar) |
|---|---|---|
| ![line](assets/screenshot_line.png) | ![pie](assets/screenshot_pie.png) | ![bar](assets/screenshot_bar.png) |

---

## 🛠️ Tech Stack

- **UI**: [Gradio 4](https://gradio.app) — Blocks API with custom dark-indigo CSS
- **NLP**: Rule-based keyword engine built with [NLTK](https://nltk.org)
- **SQL Generation**: Template-based (mock LLM) · [OpenAI](https://openai.com) GPT-3.5-turbo (optional)
- **Database**: SQLite via Python's built-in `sqlite3`
- **Charts**: [Plotly](https://plotly.com/python/) — themed to match the dark-SaaS aesthetic
- **Data Processing**: [pandas](https://pandas.pydata.org)

---

## 🏗️ Project Architecture

```
promptlytics/
├── app.py               ← Gradio UI + pipeline orchestration
├── config.py            ← Schema, keyword dicts, column synonyms
├── db.py                ← SQLite connection + safe query execution
├── sql_builder.py       ← Intent dict → parameterized SQL (Module 3)
├── visualizer.py        ← chart-type selection + Plotly figure builder
├── insights.py          ← Insights tab markdown generator
├── llm.py               ← OpenAI GPT path (optional)
├── seed_database.py     ← Generates synthetic sales data on first run
├── nlp/
│   ├── __init__.py
│   ├── preprocessor.py  ← Tokenize · Normalize · Remove stopwords (Module 1)
│   └── intent_engine.py ← Intent classify + entity extraction (Module 2)
├── data/
│   └── promptlytics.db  ← Auto-generated SQLite file (git-ignored)
├── assets/              ← Screenshots / static assets
├── requirements.txt
├── .env.example
└── .gitignore
```

### NLP Pipeline (Rule-based "Mock LLM")

```
Raw Query
   │
   ▼
[Preprocessor]   Tokenize → Lowercase → Strip punctuation → Remove stopwords
   │
   ▼
[Intent Engine]  Keyword scoring → Intent type (AGGREGATE / GROUP / FILTER / SELECT)
                 Entity extraction → measure column · dimension column · filters
   │
   ▼
[SQL Builder]    Instantiate SQL template → parameterized (sql, params) tuple
   │
   ▼
[Database]       sqlite3.execute(sql, params) → pandas DataFrame
   │
   ▼
[Visualizer]     Rule-based chart selection → Plotly Figure
   │
   ▼
[Insights]       Statistical summary → Markdown
```

---

## 🚀 Setup & Run

### 1. Clone the repository
```bash
git clone https://github.com/ayazalii/promptlytics.git
cd promptlytics
```

### 2. Create a virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure OpenAI
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY, or paste it directly in the UI
```

### 5. Seed the database (optional — auto-runs on first launch)
```bash
python seed_database.py
```

### 6. Launch the app
```bash
python app.py
```
Open [http://localhost:7860](http://localhost:7860) in your browser.

---

## 💬 Example Queries

| Query | Chart Type |
|---|---|
| `What is the monthly revenue trend?` | Line chart |
| `Show quantity sold by product` | Pie / Donut chart |
| `Which region has the highest sales?` | Bar chart |
| `How many sales records are there?` | Indicator (big number) |
| `Top 3 products by total revenue` | Bar chart |
| `Show revenue for the North region` | Table / filtered results |
| `What is the average unit price?` | Indicator |

---

## 🧠 Intent Classification Rules

The rule-based engine (mock LLM) classifies each query into one of four intent types:

| Intent | Triggers | Example |
|---|---|---|
| `AGGREGATE` | `total`, `average`, `count`, `max`, `min`, `how many` | *"What is the total revenue?"* |
| `GROUP` | `by`, `per`, `each`, `trend`, `monthly` | *"Revenue by region"* |
| `FILTER` | `where`, `greater`, `less`, `only`, categorical values | *"Sales in the North region"* |
| `SELECT` | No strong signal | *"Show me the data"* |

---

## 👥 Team

| Name | Role |
|---|---|
| Ayaz Ali | Developer |
| Chinmay Suthar | Developer |
| Mr. Mohd. Talib (Xebia) | Supervisor |

---

## 📄 License

This project was developed for academic purposes at JECRC University.  
Feel free to fork and build on it.
