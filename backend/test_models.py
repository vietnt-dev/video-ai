import os
from openai import OpenAI

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise SystemExit("Set GEMINI_API_KEY before running this script.")

client = OpenAI(
    api_key=api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

try:
    models = client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print(e)
