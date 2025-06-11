
import re
from io import BytesIO
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

###############################################################################
# Streamlit configuration
###############################################################################

st.set_page_config(
    page_title="Planning PDF Keyword Scanner",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📄 Planning PDF Keyword Scanner")

################################################################################
# Sidebar – user inputs
################################################################################

st.sidebar.header("🔍 Search settings")

# Default keyword set – feel free to edit/expand
DEFAULT_KEYWORDS = [
    "construction",
    "height",
    "traffic",
    "parking",
    "heritage",
    "green belt",
    "biodiversity",
    "affordable housing",
]

def _format_default_keywords(kw_list: list[str]) -> str:
    """Return comma-separated keyword string suitable for the text area default."""
    return ", ".join(sorted(set(kw_list)))

keywords_input = st.sidebar.text_area(
    "Keywords to search (comma-separated)",
    value=_format_default_keywords(DEFAULT_KEYWORDS),
    height=120,
    help="Edit the list or paste your own keywords, separated by commas.",
)

# Convert keyword input into a clean list – strip whitespace, ignore empties
def _parse_keywords(s: str) -> list[str]:
    return [k.strip() for k in s.split(",") if k.strip()]

keywords = _parse_keywords(keywords_input)

st.sidebar.markdown(
    f"**{len(keywords)} keyword(s)** will be searched: {', '.join(keywords)}"
)

# Context window controls
context_window = st.sidebar.slider(
    "Context window (characters before/after match)",
    min_value=20,
    max_value=200,
    value=60,
    step=10,
)

################################################################################
# Main – file uploader & processing
################################################################################

uploaded_files = st.file_uploader(
    "Upload one or more PDF documents (hold ⌘/Ctrl to select multiple)",
    type=["pdf"],
    accept_multiple_files=True,
)

run_btn = st.button(
    "🚀 Run scan", disabled=not uploaded_files, type="primary", use_container_width=True
)

################################################################################
# Utility functions
################################################################################

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Return the concatenated text of a PDF file using pdfplumber."""
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def find_snippets(text: str, keyword: str, window: int) -> list[str]:
    """Return list of context snippets around each keyword match."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    snippets: list[str] = []
    for match in pattern.finditer(text):
        start, end = match.span()
        snippet = text[max(0, start - window) : min(len(text), end + window)]
        snippets.append(snippet.replace("\n", " "))
    return snippets

def highlight(snippet: str, keyword: str) -> str:
    """Return snippet as Markdown with **bold** highlights around keyword."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda m: f"**{m.group(0)}**", snippet)

################################################################################
# Scan action
################################################################################

if run_btn and uploaded_files:
    results = []  # list[dict]
    progress = st.progress(0.0, text="Scanning PDFs…")

    for idx, file in enumerate(uploaded_files):
        file_name = file.name
        text = extract_text_from_pdf(file.read())

        for kw in keywords:
            snippets = find_snippets(text, kw, context_window)
            for snippet in snippets:
                results.append(
                    {
                        "File": file_name,
                        "Keyword": kw,
                        "Snippet": snippet,
                    }
                )

        progress.progress((idx + 1) / len(uploaded_files), text=f"Processed {idx+1}/{len(uploaded_files)} PDFs")

    progress.empty()

    if not results:
        st.info("No keywords were found in the uploaded documents.")
    else:
        df = pd.DataFrame(results)

        # Show interactive data table with highlights
        st.subheader("🔎 Results")

        for kw in keywords:
            mask = df["Keyword"].str.lower() == kw.lower()
            df.loc[mask, "Snippet"] = df.loc[mask, "Snippet"].apply(lambda s, _kw=kw: highlight(s, _kw))

        st.dataframe(df, use_container_width=True, height=500)

        # Provide CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download results as CSV",
            data=csv,
            file_name="keyword_scan_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

################################################################################
# Footer
################################################################################

st.markdown(
    """---
*Built with ❤️ using Streamlit & pdfplumber.*""",
    unsafe_allow_html=True,
)
