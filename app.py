"""
GraphRAG Guard — app.py
------------------------
Single-folder entry point. Run with:
    streamlit run app.py

repo_parser.py, cognee_service.py, and report_generator.py sit in this same
folder, so they're imported directly with no path tricks.
"""

import os
import traceback
import zipfile

import streamlit as st
from dotenv import load_dotenv

from repo_parser import extract_and_merge_repo
from cognee_service import (
    THREAT_DATASET,
    connect_to_cognee_cloud,
    disconnect_from_cognee_cloud,
    ingest_threat_intel,
    recall_relevant_threats,
    RecallNotReadyError,
)
from report_generator import generate_appsec_report

load_dotenv()  # reads .env sitting in this same folder

st.set_page_config(page_title="GraphRAG Guard", layout="wide")

if "cognee_connected" not in st.session_state:
    st.session_state["cognee_connected"] = False
if "threat_intel_ingested" not in st.session_state:
    st.session_state["threat_intel_ingested"] = False

st.title("🛡️ GraphRAG Guard")
st.caption(
    "Contextual AppSec vulnerability scanner — cross-references your codebase against a "
    "graph-mapped threat-intelligence memory (Cognee Cloud + Gemini)."
)

# --------------------------------------------------------------------------- #
# Sidebar: configuration + connection + threat intel ingestion
# --------------------------------------------------------------------------- #

with st.sidebar:
    st.header("⚙️ Configuration")

    gemini_api_key = st.text_input(
        "Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", "")
    )
    cognee_url = st.text_input(
        "Cognee Cloud Instance URL", value=os.getenv("COGNEE_URL", "https://your-instance.cognee.ai")
    )
    cognee_api_key = st.text_input(
        "Cognee Cloud API Key (optional)", type="password", value=os.getenv("COGNEE_API_KEY", "")
    )

    st.divider()

    if st.session_state["cognee_connected"]:
        st.success("Connected to Cognee Cloud")
        if st.button("Disconnect"):
            disconnect_from_cognee_cloud()
            st.session_state["cognee_connected"] = False
            st.rerun()
    else:
        if st.button("🔌 Connect to Cognee Cloud", use_container_width=True):
            if not (gemini_api_key and cognee_url):
                st.error("Gemini API key and Cognee URL are required.")
            else:
                with st.spinner("Connecting to company-hosted Cognee instance..."):
                    try:
                        connect_to_cognee_cloud(
                            cognee_url,
                            gemini_api_key,
                            cognee_api_key=cognee_api_key or None,
                        )
                        st.session_state["cognee_connected"] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Connection failed: {e}")
                        st.code(traceback.format_exc())

    st.divider()
    st.subheader("📚 Threat Intelligence Ingestion")
    st.caption("Upload CVE writeups, OWASP notes, or internal findings (.txt/.md) to grow the graph.")

    intel_file = st.file_uploader("Threat intel document", type=["txt", "md"], key="intel_upload")
    if st.button("Ingest into Threat Graph", use_container_width=True):
        if not st.session_state["cognee_connected"]:
            st.error("Connect to Cognee Cloud first.")
        elif not intel_file:
            st.error("Upload a threat-intel document first.")
        else:
            with st.spinner("Running remember() — add → cognify → improve..."):
                try:
                    text = intel_file.read().decode("utf-8", errors="ignore")
                    ingest_threat_intel(text)
                    st.session_state["threat_intel_ingested"] = True
                    st.success(f"Ingested '{intel_file.name}' into the '{THREAT_DATASET}' graph.")
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
                    st.code(traceback.format_exc())

    if st.session_state["threat_intel_ingested"]:
        st.caption("✅ Threat graph has ingested data this session.")
    else:
        st.caption("⚠️ No threat intel ingested yet this session — recall will run on an empty graph.")

# --------------------------------------------------------------------------- #
# Main: repository scan
# --------------------------------------------------------------------------- #

st.subheader("📦 Upload Project Repository")
uploaded_zip = st.file_uploader("Upload a .zip of your project", type=["zip"])

scan_clicked = st.button("🔍 Scan Repository", type="primary", disabled=uploaded_zip is None)

if scan_clicked:
    if not st.session_state["cognee_connected"]:
        st.error("Connect to Cognee Cloud in the sidebar before scanning.")
    elif not gemini_api_key:
        st.error("Gemini API key is required to generate the report.")
    else:
        try:
            with st.spinner("Unpacking and parsing repository..."):
                code_payload, included_files = extract_and_merge_repo(uploaded_zip)

            if not code_payload.strip():
                st.warning(
                    "No files matching supported extensions (.py, .js, .ts, .json, .go) were found."
                )
            else:
                st.info(f"Parsed {len(included_files)} source file(s).")
                with st.expander("Files included in this scan"):
                    st.code("\n".join(included_files))

                with st.spinner("Querying graph-linked threat intelligence via cognee.recall()..."):
                    try:
                        threat_context = recall_relevant_threats(code_payload)
                    except RecallNotReadyError as e:
                        st.warning(
                            f"{e}\n\nContinuing with code-only analysis (no graph context) for this scan."
                        )
                        threat_context = (
                            "No threat-intelligence graph data available yet — "
                            "this analysis relies on the model's own knowledge only."
                        )

                with st.spinner("Generating executive AppSec report with Gemini 2.5 Flash..."):
                    report_markdown = generate_appsec_report(code_payload, threat_context, gemini_api_key)

                st.divider()
                st.markdown(report_markdown)

                st.download_button(
                    "⬇️ Download Report (Markdown)",
                    data=report_markdown,
                    file_name="graphrag_guard_report.md",
                    mime="text/markdown",
                )

        except zipfile.BadZipFile:
            st.error("The uploaded file is not a valid .zip archive.")
        except Exception as e:
            st.error(f"Scan failed: {e}")
            st.code(traceback.format_exc())