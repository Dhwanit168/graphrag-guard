"""
cognee_service.py
------------------
Thin service layer around Cognee Cloud's hybrid graph+vector memory.

Uses the current "V2" simplified memory API:
    cognee.serve()      -> bind SDK to a company-hosted Cognee Cloud instance
    cognee.remember()   -> ingest text into a named dataset (runs add -> cognify -> improve)
    cognee.recall()     -> hybrid graph/vector query against one or more datasets
    cognee.disconnect() -> release the cloud session

NOTE: remember() takes `dataset_name` (singular str); recall() takes
`datasets` (a list). There is no `dataset=` kwarg on either — that's a
common mistake that will raise a TypeError at runtime.
"""

import os
import asyncio

import cognee

THREAT_DATASET = "threat_intelligence"

# Cognee is routed through LiteLLM, which requires the "gemini/" model prefix.
LLM_MODEL = "gemini/gemini-2.5-flash"
EMBEDDING_MODEL = "gemini/gemini-embedding-001"

MAX_RECALL_QUERY_CHARS = 12_000  # keep the recall query focused/cheap

# --------------------------------------------------------------------------- #
# cognee.serve() opens a persistent aiohttp session bound to whatever event
# loop is active at connect time. If every call creates-and-closes its own
# loop (asyncio.run() does this), later calls try to reuse a session tied to
# an already-closed loop -> "RuntimeError: Event loop is closed". The fix is
# to keep ONE event loop alive for the whole app process and run every
# Cognee call (connect/remember/recall/disconnect) on that same loop.
# --------------------------------------------------------------------------- #

_event_loop: asyncio.AbstractEventLoop | None = None


def _get_loop() -> asyncio.AbstractEventLoop:
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
    return _event_loop


def run_async(coro):
    """
    Bridges Cognee's async API into Streamlit's synchronous callback model,
    always reusing the same long-lived event loop so Cognee's internal
    aiohttp session stays valid across connect / remember / recall calls.
    """
    loop = _get_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def configure_cognee_env(gemini_api_key: str) -> None:
    """Point Cognee's LLM + embedding layer at Gemini via LiteLLM env vars."""
    os.environ["LLM_PROVIDER"] = "gemini"
    os.environ["LLM_MODEL"] = LLM_MODEL
    os.environ["LLM_API_KEY"] = gemini_api_key

    os.environ["EMBEDDING_PROVIDER"] = "gemini"
    os.environ["EMBEDDING_MODEL"] = EMBEDDING_MODEL
    os.environ["EMBEDDING_API_KEY"] = gemini_api_key


async def _connect(cognee_url: str, cognee_api_key: str | None):
    if cognee_api_key:
        await cognee.serve(url=cognee_url, api_key=cognee_api_key)
    else:
        # Some company-hosted instances run with REQUIRE_AUTHENTICATION=false,
        # in which case no api_key is needed at all.
        await cognee.serve(url=cognee_url)


async def _disconnect():
    await cognee.disconnect()


async def _remember(text: str, dataset_name: str):
    return await cognee.remember(data=text, dataset_name=dataset_name)


async def _recall(query_text: str, dataset_name: str):
    return await cognee.recall(query_text=query_text, datasets=[dataset_name])


def connect_to_cognee_cloud(cognee_url: str, gemini_api_key: str, cognee_api_key: str | None = None) -> None:
    configure_cognee_env(gemini_api_key)
    run_async(_connect(cognee_url, cognee_api_key))


def disconnect_from_cognee_cloud() -> None:
    global _event_loop
    run_async(_disconnect())
    if _event_loop is not None and not _event_loop.is_closed():
        _event_loop.close()
    _event_loop = None


def ingest_threat_intel(text: str) -> None:
    """One-time (or periodic) ingestion of the threat-intel corpus into the graph."""
    run_async(_remember(text, THREAT_DATASET))


class RecallNotReadyError(Exception):
    """Raised when recall() is called before the dataset has any cognified data."""


def recall_relevant_threats(code_payload: str) -> str:
    """
    Queries Cognee's hybrid graph+vector memory using the parsed codebase as
    the query signal, returning graph-linked threat intelligence relevant to
    the patterns actually present in the repo.

    Never raises on an empty/not-yet-ready graph -- falls back to a plain
    message instead, so a missing ingestion step degrades the report rather
    than crashing the whole scan.
    """
    query_text = code_payload[:MAX_RECALL_QUERY_CHARS]

    try:
        results = run_async(_recall(query_text, THREAT_DATASET))
    except RuntimeError as e:
        message = str(e)
        if "Recall prerequisites not met" in message or "404" in message:
            raise RecallNotReadyError(
                "The threat_intelligence dataset has no ingested data yet. "
                "Upload a document and click 'Ingest into Threat Graph' first."
            ) from e
        raise  # anything else (401, 5xx, network) should surface as a real error

    if not results:
        return "No directly linked threat-intelligence entries were found in the graph."

    return "\n\n".join(str(r) for r in results)