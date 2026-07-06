# 🛡️ GraphRAG Guard

**A contextual AppSec vulnerability scanner that cross-references your codebase against a graph-mapped threat-intelligence memory — built for the WeMakeDevs Hangover Hackathon.**

Most AI code scanners are a thin wrapper: dump your code into an LLM prompt and hope it remembers enough security knowledge to say something useful. GraphRAG Guard does something different — it maintains a real, queryable **knowledge graph of threat intelligence** (CVE writeups, OWASP patterns, internal findings) using [Cognee](https://www.cognee.ai/)'s hybrid graph+vector memory, and cross-references your uploaded repository against that graph before generating a report. Findings are backed by graph-linked evidence, not just an LLM's raw judgment.

---

## 🚩 The Problem

Traditional static analyzers rely on rigid rule sets and miss context. Plain "ask an LLM to review this code" tools have no persistent memory — every scan starts from zero, with no way to accumulate and reuse threat intelligence across scans or connect a vulnerability pattern in your code to *why* it's dangerous, based on real-world precedent.

## 💡 The Approach

1. **Build a threat-intelligence graph once.** Feed in CVE writeups, OWASP notes, or internal security findings. Cognee turns this into a persistent, queryable knowledge graph — not just embeddings, but entities and relationships.
2. **Parse the target repo.** Upload a `.zip`, and GraphRAG Guard safely extracts and merges every source file into one structured payload.
3. **Cross-reference, don't guess.** The parsed code is used as a query against the threat-intelligence graph via hybrid graph/vector recall — surfacing intel that's actually *linked* to patterns in your code, not just keyword-matched.
4. **Generate an executive report.** Gemini 2.5 Flash takes the code + retrieved graph context and produces a structured markdown AppSec dashboard: severity, impact tracing, and concrete remediation.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────┐
                    │   Threat Intel Corpus    │
                    │  (CVE / OWASP / .md)     │
                    └────────────┬────────────┘
                                 │  cognee.remember()
                                 ▼
                    ┌─────────────────────────┐
                    │   Cognee Cloud (Graph +  │
                    │   Vector Hybrid Memory)  │
                    └────────────┬────────────┘
                                 │  cognee.recall()
                                 ▲
                                 │  code payload as query
                    ┌────────────┴────────────┐
   .zip Upload ───► │   repo_parser.py         │
                    │   (safe extract + merge) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Gemini 2.5 Flash        │
                    │  (report_generator.py)  │
                    └────────────┬────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  Streamlit Executive     │
                    │  AppSec Dashboard        │
                    └─────────────────────────┘
```

---

## ✨ Features

- **Graph-linked threat intelligence** — not flat vector similarity search, but Cognee's hybrid graph+vector recall
- **Safe ZIP ingestion** — zip-slip-guarded extraction, filters to `.py`, `.js`, `.ts`, `.json`, `.go`
- **Company-hosted Cognee Cloud integration** — connects to a real hosted memory instance, not just local storage
- **Executive-ready markdown reports** — Severity / Impact Tracing / Remediation, rendered natively in Streamlit, downloadable as `.md`
- **Graceful degradation** — if the threat graph is empty or unreachable, the scan still completes using code-only analysis instead of crashing

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| UI | [Streamlit](https://streamlit.io/) |
| Graph + vector memory | [Cognee Cloud](https://www.cognee.ai/) (`remember()` / `recall()`) |
| Report generation | Google Gemini 2.5 Flash via the [`google-genai`](https://pypi.org/project/google-genai/) SDK |
| Embeddings | `gemini-embedding-001` |

---

## 📁 Project Structure

```
graphrag-guard/
├── app.py                # Streamlit UI — entry point
├── repo_parser.py         # Safe ZIP extraction + source file merging
├── cognee_service.py      # Cognee Cloud connection, remember/recall wrappers
├── report_generator.py    # Gemini prompt + executive report generation
├── requirements.txt
├── .env.example           # Template for required environment variables
└── .env                   # Your real keys (gitignored, never commit this)
```

Single folder, single process — no separate backend server. Streamlit's synchronous script-rerun model *is* the request/response cycle here.

---

## 🚀 Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd graphrag-guard

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Get your credentials

- **Gemini API key** → [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- **Cognee Cloud Base URL + API key** → from your Cognee Cloud dashboard's API Keys page (tenant-specific, not a shared URL)

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_real_gemini_key
COGNEE_URL=https://your-tenant.aws.cognee.ai
COGNEE_API_KEY=your_real_cognee_api_key
```

### 4. Run

```bash
streamlit run app.py
```

---

## 🖱️ Usage

| Step | Action | What happens |
|---|---|---|
| 1 | Sidebar → **Connect to Cognee Cloud** | Binds the SDK to your hosted instance via `cognee.serve()` |
| 2 | Sidebar → upload a `.txt`/`.md` threat-intel doc → **Ingest into Threat Graph** | `cognee.remember()` runs add → cognify → improve, building the graph |
| 3 | Main → upload project `.zip` → **Scan Repository** | Extracts, merges, cross-references via `cognee.recall()`, then generates the report with Gemini |
| 4 | — | Executive AppSec report renders inline; download as markdown |

**Important:** step 2 must complete successfully *before* step 3 for graph-linked findings — scanning against an empty threat graph still works, but falls back to code-only analysis.

---

## ⚠️ Known Limitations

- Cognee's `remember()` ingestion runs a background indexing pipeline; very large threat-intel documents may need a few seconds before `recall()` reflects them.
- Recall queries are truncated to the first ~12,000 characters of the merged code payload to keep queries fast and focused; extremely large repos may not have every file represented in the graph query (though the full payload is still sent to Gemini for report generation).
- This is a hackathon build — no persistent report history / multi-user session management.

---

## 🙌 Built With

- [Cognee](https://www.cognee.ai/) — hybrid graph+vector AI memory
- [Google Gemini](https://ai.google.dev/) — 2.5 Flash for report generation, `gemini-embedding-001` for embeddings
- [Streamlit](https://streamlit.io/) — UI

Built for the **WeMakeDevs Hangover Hackathon**.
