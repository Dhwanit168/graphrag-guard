"""
report_generator.py
--------------------
Builds the final executive AppSec report by handing the parsed codebase and
Cognee-retrieved threat-intel context directly to Gemini 2.5 Flash.
"""

from google import genai

MAX_REPORT_INPUT_CHARS = 300_000  

REPORT_PROMPT_TEMPLATE = """You are a Principal Application Security Architect producing an
executive-facing vulnerability assessment. Analyze the SOURCE CODE below using the
GRAPH-LINKED THREAT INTELLIGENCE context as supporting evidence for your findings.

Respond ONLY in GitHub-flavored Markdown, following EXACTLY this structure so it renders
cleanly as a Streamlit dashboard:

# 🛡️ GraphRAG Guard — Executive AppSec Report

## Overview
A 2-3 sentence summary of overall risk posture.

## 🔴 Findings by Severity

For each vulnerability found, output a subsection in this exact format:

### [SEVERITY] — Short Title
- **File(s):** path/to/file.ext (line reference if identifiable)
- **CWE / Category:** e.g. CWE-89 SQL Injection
- **Impact Tracing:** explain how an attacker could reach and exploit this from an entry
  point, referencing the graph-linked threat intel where relevant.
- **Remediation:**
  ```
  <a short corrected code snippet or concrete fix>
  ```

Use SEVERITY as one of: CRITICAL, HIGH, MEDIUM, LOW. Order findings from most to least severe.

## ✅ Summary Table

| Severity | Count |
|----------|-------|
| Critical | n     |
| High     | n     |
| Medium   | n     |
| Low      | n     |

## 📌 Recommended Next Steps
A short prioritized action list.

--------------------------------------------------------------------------------
GRAPH-LINKED THREAT INTELLIGENCE CONTEXT (retrieved via Cognee hybrid recall):
{threat_context}

--------------------------------------------------------------------------------
SOURCE CODE PAYLOAD:
{code_payload}
"""


def generate_appsec_report(code_payload: str, threat_context: str, gemini_api_key: str) -> str:
    client = genai.Client(api_key=gemini_api_key)

    prompt = REPORT_PROMPT_TEMPLATE.format(
        threat_context=threat_context,
        code_payload=code_payload[:MAX_REPORT_INPUT_CHARS],
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text
