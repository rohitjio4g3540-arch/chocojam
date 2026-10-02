import os

from dotenv import load_dotenv
from fastapi import FastAPI
from openai import OpenAI

from memory.memory_manager import (
    get_profile,
    get_projects,
    get_knowledge,
    get_conversations,
    update_project,
    add_conversation,
)

from tools.web_search import web_search
from tools.tool_registry import list_tools


load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


app = FastAPI()


MODEL = "zai-org/GLM-5.3"
NEBIUS_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"


@app.get("/")
def root():
    return {
        "message": "ChocoJam is running"
    }


@app.get("/memory")
def get_memory():
    return {
        "profile": get_profile(),
        "projects": get_projects(),
        "knowledge": get_knowledge(),
        "conversations": get_conversations(),
    }


@app.get("/search")
def search_web(query: str, max_results: int = 5):
    return {
        "results": web_search(query, max_results)
    }


@app.get("/tools")
def get_tools():
    return {
        "tools": list_tools()
    }


@app.post("/ask-model")
def ask_model(input_text: str):
    api_key = os.getenv("NEBIUS_API_KEY")

    if not api_key:
        return {
            "error": "NEBIUS_API_KEY is not loaded"
        }

    client = OpenAI(
        base_url=NEBIUS_BASE_URL,
        api_key=api_key,
    )

    memory = {
        "profile": get_profile(),
        "projects": get_projects(),
        "knowledge": get_knowledge(),
    }

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are ChocoJam, a personal second-brain AI agent. "
                    "Use the provided memory as context when relevant.\n\n"
                    f"Memory:\n{memory}"
                ),
            },
            {
                "role": "user",
                "content": input_text,
            },
        ],
    )

    response_text = response.choices[0].message.content

    if input_text.lower().startswith("remember that"):
        project_text = input_text[len("remember that"):].strip()

        update_project(
            "latest",
            project_text,
        )

    add_conversation(
        user_message=input_text,
        assistant_message=response_text,
    )

    return {
        "response": response_text
    }