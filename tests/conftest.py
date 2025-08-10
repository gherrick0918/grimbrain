# tests/conftest.py
import os, sys, pathlib, pytest
from llama_index.core.settings import Settings

# Robust import for different LlamaIndex versions
try:
    from llama_index.core.llms.mock import MockLLM
except Exception:  # older versions
    from llama_index.llms.mock import MockLLM  # type: ignore

# Make tests use a mock LLM so nothing tries to hit OpenAI
os.environ["IS_TESTING"] = "1"      # resolve_llm("default") will pick MockLLM
Settings.llm = MockLLM()            # and Settings.llm is explicitly set

# Make sure tests can import your local modules (query_router, etc.)
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Try the HF embedder; skip tests with a clear message if it's missing
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    _HAS_HF = True
except Exception:
    _HAS_HF = False

@pytest.fixture(scope="session", autouse=True)
def require_store():
    if not os.path.isdir("chroma_store"):
        pytest.skip("No persisted chroma_store found. Run your indexer first.")

@pytest.fixture(scope="session")
def embedder():
    if not _HAS_HF:
        pytest.skip(
            "HuggingFace embedder not available. "
            "Install with: pip install -U llama-index llama-index-embeddings-huggingface"
        )
    model_name = os.getenv("MODEL_NAME", "BAAI/bge-small-en-v1.5")
    emb = HuggingFaceEmbedding(model_name=model_name)
    Settings.embed_model = emb
    return emb
