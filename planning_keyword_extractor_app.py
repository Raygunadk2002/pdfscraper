import io
import re
import tempfile
import zipfile
from pathlib import Path
from typing import List

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

st.title("📄 Planning PDF Keyword Scanner – Large Batch Edition")

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


def _format_default_keywords(kw_list: List[str]) -> str:
    """Return comma‑separated keyword string suitable for the text area default."""
    return ", ".join(sorted(set(kw_list)))


keywords_input = st.sidebar.text_area(
    "Keywords to search (comma‑separated)",
    value=_format_default_keywords(DEFAULT_KEYWORDS),
    height=120,
    help="Edit the list or paste your own keywords, separated by commas.",
)


def _parse_keywords(s: str) -> List[str]:
    """Convert the textarea value to a clean keyword list."""
    return [k.strip() for k in s.split(",") if k.strip()]


keywords = _parse_keywords(keywords_input)

st.sidebar.markdown(
    f"**{len(keywords)} keyword(s)** will be searched: {', '.join(keywords)}"
)

# Context window controls
context_window = st.sidebar.slider(
    "Context window (characters before/after match)",
    min_value=20,
    max_value=400,
    value=60,
    step=10,
)

################################################################################
# File uploader – now accepts ZIPs containing many PDFs
################################################################################

uploaded_files = st.file_uploader(
    "Upload PDF files **or** ZIP archives (Ctrl/⌘‑click for multi‑select)",
    type=["pdf", "zip"],
    accept_multiple_files=True,
)

run_btn = st.button(
    "🚀 Run scan", disabled=not uploaded_files, type="primary", use_container_width=True
)

################################################################################
# Utility functions
################################################################################


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Return the concatenated text of a PDF file using pdfplumber."""
    with pdfplumber.open(str(pdf_path)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def find_snippets(text: str, keyword: str, window: int) -> List[str]:
    """Return list of context snippets around each keyword match."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    snippets: List[str] = []
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
# Helper – gather all PDF paths from uploads (supports ZIP archives)
################################################################################


def gather_pdf_paths(temp_dir: Path) -> List[Path]:
    """Write uploaded files to *temp_dir* and return a list of PDF Paths."""
    pdf_paths: List[Path] = []

    for uploaded in uploaded_files:
        filename = uploaded.name
        if filename.lower().endswith(".zip"):
            # Treat as archive – extract PDFs into temp_dir
            with zipfile.ZipFile(io.BytesIO(uploaded.read())) as zf:
                for member in zf.namelist():
                    if member.lower().endswith(".pdf"):
                        dest = temp_dir / Path(member).name
                        dest.write_bytes(zf.read(member))
                        pdf_paths.append(dest)
        else:
            # Single PDF – write into temp_dir
            dest = temp_dir / filename
            dest.write_bytes(uploaded.read())
            pdf_paths.append(dest)

    return pdf_paths

################################################################################
# Main – Scan action
################################################################################

if run_btn and uploaded_files:
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        pdf_paths = gather_pdf_paths(temp_dir)

        if not pdf_paths:
            st.warning("No PDFs found inside the uploads.")
            st.stop()

        results = []  # list[dict]
        progress = st.progress(0.0, text="Scanning PDFs…")

        for idx, pdf_path in enumerate(pdf_paths, 1):
            try:
                text = extract_text_from_pdf(pdf_path)
            except Exception as e:
                st.error(f"❌ Failed to read {pdf_path.name}: {e}")
                continue

            for kw in keywords:
                snippets = find_snippets(text, kw, context_window)
                for snippet in snippets:
                    results.append(
                        {
                            "File": pdf_path.name,
                            "Keyword": kw,
                            "Snippet": snippet,
                        }
                    )

            progress.progress(idx / len(pdf_paths), text=f"Processed {idx}/{len(pdf_paths)} PDFs")

        progress.empty()

    # Display results after temp_dir is cleaned up (to free space early)
    if not results:
        st.info("No keywords were found in the uploaded documents.")
    else:
        df = pd.DataFrame(results)

        st.subheader("🔎 Results")

        # Highlighting
        for kw in keywords:
            mask = df["Keyword"].str.lower() == kw.lower()
            df.loc[mask, "Snippet"] = df.loc[mask, "Snippet"].apply(lambda s, _kw=kw: highlight(s, _kw))

        st.dataframe(df, use_container_width=True, height=600)

        # CSV download
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download results as CSV",
            data=csv,
            file_name="keyword_scan_results.csv",
            mime="text/csv",
            use_container_width=True,
        )

################################################################################
# Footer + extra tips for big batches
################################################################################

with st.expander("ℹ️ Tips for processing hundreds of PDFs"):
    st.markdown(
        """
* **Upload ZIP archives** – zipping 500 PDFs into a single file avoids browser-side multi‑select limits and speeds up the transfer.
* For files >200 MB create a `.streamlit/config.toml` next to this script with:

```toml
[server]
maxUploadSize = 2000  # MB (adjust)
maxMessageSize = 2000
```

* The app now streams each PDF to disk before reading it, keeping RAM usage low – you can comfortably handle hundreds of typical planning docs on a 1‑2 GB instance.
        """
    )

st.markdown(
    """---\n*Built with ❤️ using Streamlit & pdfplumber. Supports hundreds of PDFs via ZIP upload.*""",
    unsafe_allow_html=True,
)