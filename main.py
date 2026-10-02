import json
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
from tools.tool_registry import (
    list_tools,
    execute_tool,
)


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


def get_model_client():
    api_key = os.getenv("NEBIUS_API_KEY")

    if not api_key:
        raise ValueError("NEBIUS_API_KEY is not loaded")

    return OpenAI(
        base_url=NEBIUS_BASE_URL,
        api_key=api_key,
    )


def build_memory():
    return {
        "profile": get_profile(),
        "projects": get_projects(),
        "knowledge": get_knowledge(),
    }


def build_tool_descriptions():
    return [
        {
            "name": "web_search",
            "description": (
                "Search the public web for current information. "
                "Use this when the user needs research, current facts, "
                "sources, or information that may have changed."
            ),
            "parameters": {
                "query": "string",
                "max_results": "integer, optional",
            },
        },
        {
            "name": "list_files",
            "description": (
                "List files available inside the ChocoJam project. "
                "Use this when the user asks what files exist or "
                "needs to inspect the project structure."
            ),
            "parameters": {},
        },
        {
            "name": "read_file",
            "description": (
                "Read the contents of a text file inside the ChocoJam "
                "project. Use this when the user asks about the contents "
                "of a specific project file."
            ),
            "parameters": {
                "path": "string",
            },
        },
    ]


def choose_tool(client, input_text, memory):
    tool_descriptions = build_tool_descriptions()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the tool-selection component of ChocoJam.\n\n"
                    "Decide whether the user's request requires a tool.\n"
                    "Only select a tool when it is genuinely useful for "
                    "answering the user's request.\n\n"
                    "Available tools:\n"
                    f"{json.dumps(tool_descriptions, indent=2)}\n\n"
                    "Return ONLY valid JSON in this format:\n"
                    '{"use_tool": false}\n'
                    "or\n"
                    '{"use_tool": true, "tool": "web_search", '
                    '"arguments": {"query": "...", "max_results": 5}}\n\n'
                    "For list_files, use:\n"
                    '{"use_tool": true, "tool": "list_files", '
                    '"arguments": {}}\n\n'
                    "For read_file, use:\n"
                    '{"use_tool": true, "tool": "read_file", '
                    '"arguments": {"path": "example.txt"}}\n\n'
                    f"Memory:\n{json.dumps(memory, ensure_ascii=False)}"
                ),
            },
            {
                "role": "user",
                "content": input_text,
            },
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "use_tool": False
        }


def generate_response(client, input_text, memory, tool_result=None):
    system_content = (
        "You are ChocoJam, a personal second-brain AI agent.\n\n"
        "Your primary goal is to answer the user's actual request clearly "
        "and directly.\n\n"
        "Use memory only when it is relevant to the user's request.\n"
        "Do not add unsolicited recommendations, project advice, "
        "hackathon commentary, or unrelated context.\n"
        "Do not mention ChocoJam's internal architecture unless the user "
        "asks about it.\n"
        "Do not force the user's current project into unrelated answers.\n"
        "Do not invent facts.\n\n"
        f"Memory:\n{json.dumps(memory, ensure_ascii=False)}"
    )

    if tool_result is not None:
        system_content += (
            "\n\nA tool was executed for this request.\n"
            "Use its results when answering the user.\n"
            "Do not invent facts that are not supported by the tool results.\n"
            "When using information from web results, preserve the source "
            "title and URL so the caller can verify it.\n\n"
            f"Tool result:\n{json.dumps(tool_result, ensure_ascii=False)}"
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_content,
            },
            {
                "role": "user",
                "content": input_text,
            },
        ],
    )

    return response.choices[0].message.content


def run_agent_task(client, input_text):
    memory = build_memory()

    tool_decision = choose_tool(
        client,
        input_text,
        memory,
    )

    tool_result = None
    tool_used = None
    sources = []

    if tool_decision.get("use_tool") is True:
        tool_name = tool_decision.get("tool")
        arguments = tool_decision.get("arguments", {})

        try:
            tool_result = execute_tool(
                tool_name,
                **arguments,
            )

            tool_used = tool_name

            if tool_name == "web_search" and isinstance(tool_result, list):
                sources = [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", ""),
                    }
                    for result in tool_result
                    if result.get("url")
                ]

        except Exception as error:
            tool_result = {
                "error": str(error)
            }

    response_text = generate_response(
        client,
        input_text,
        memory,
        tool_result,
    )

    return {
        "response": response_text,
        "tool_used": tool_used,
        "sources": sources,
    }


@app.post("/ask-model")
def ask_model(input_text: str):
    try:
        client = get_model_client()
    except ValueError as error:
        return {
            "error": str(error)
        }

    result = run_agent_task(
        client,
        input_text,
    )

    if input_text.lower().startswith("remember that"):
        project_text = input_text[len("remember that"):].strip()

        update_project(
            "latest",
            project_text,
        )

    add_conversation(
        user_message=input_text,
        assistant_message=result["response"],
    )

    return result