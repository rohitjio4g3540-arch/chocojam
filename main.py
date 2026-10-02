import os

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI()

MODEL = "zai-org/GLM-5.3"
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@app.get("/")
def root():
    return {"message": "ChocoJam is running"}


@app.post("/ask-model")
def ask_model(input_text: str):
    api_key = os.getenv("NEBIUS_API_KEY")

    if not api_key:
        return {"error": "NEBIUS_API_KEY is not loaded"}

    client = OpenAI(
        base_url=NEBIUS_BASE_URL,
        api_key=api_key,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": input_text,
            }
        ],
    )

    return {
        "response": response.choices[0].message.content
    }