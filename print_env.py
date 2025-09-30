import os
import pathlib
from dotenv import load_dotenv

load_dotenv('.env')
print("CWD:", pathlib.Path().resolve())
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
print("GRIMBRAIN_AI:", os.getenv("GRIMBRAIN_AI"))
print("GRIMBRAIN_AI_CACHE_DIR:", os.getenv("GRIMBRAIN_AI_CACHE_DIR"))