
# Planning PDF Keyword Scanner

A simple Streamlit app to batch‑scan 10s–100s of planning‑related PDF documents, flagging user‑defined keywords and showing the surrounding text.

## Features
* 🔍 **Editable keyword list** – defaults provided, tweak in the sidebar.
* 📑 **Bulk PDF upload** – drag in whole folders.
* 📌 **Highlighted context snippets** – adjustable size.
* ⬇️ **CSV export** of all matches.

## Quickstart

```bash
git clone <your‑repo‑url>
cd planning_keyword_scanner
python -m venv venv && source venv/bin/activate   # optional
pip install -r requirements.txt
streamlit run planning_keyword_extractor_app.py
```

Then open the local URL that Streamlit displays.

## Folder structure

```
planning_keyword_scanner/
├── planning_keyword_extractor_app.py
├── requirements.txt
└── README.md
```

---

Built with ❤️ in June 2025.
