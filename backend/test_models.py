import os
from openai import OpenAI

client = OpenAI(
    api_key="AIzaSyCNgeuMfwXtTGX9HfN1LDglAU-1MY5EO20",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

try:
    models = client.models.list()
    for m in models.data:
        print(m.id)
except Exception as e:
    print(e)
