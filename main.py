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


def create_task_plan(client, input_text, memory):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the planning component of ChocoJam.\n\n"
                    "Create a short execution plan for the user's request.\n"
                    "The plan must contain only necessary steps.\n"
                    "Do not perform the task.\n"
                    "Do not invent information.\n\n"
                    "Available tools:\n"
                    f"{json.dumps(build_tool_descriptions(), indent=2)}\n\n"
                    f"Memory:\n"
                    f"{json.dumps(memory, ensure_ascii=False)}\n\n"
                    "Return ONLY valid JSON in this format:\n"
                    "{"
                    '"goal": "short description", '
                    '"steps": ["step 1", "step 2"]'
                    "}"
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
            "goal": input_text,
            "steps": [],
        }


def choose_tool(
    client,
    input_text,
    memory,
    plan,
    completed_steps,
    tool_results,
):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the execution component of ChocoJam.\n\n"
                    "Choose the SINGLE next tool required to advance "
                    "the user's request.\n\n"
                    "Follow the execution plan.\n"
                    "Do not repeat work that has already been completed.\n"
                    "If the available evidence is already sufficient, "
                    "return use_tool false.\n"
                    "Do not select a tool merely because one exists.\n\n"
                    "Available tools:\n"
                    f"{json.dumps(build_tool_descriptions(), indent=2)}\n\n"
                    f"Execution plan:\n"
                    f"{json.dumps(plan, ensure_ascii=False)}\n\n"
                    f"Completed tool steps:\n"
                    f"{json.dumps(completed_steps, ensure_ascii=False)}\n\n"
                    f"Previous tool results:\n"
                    f"{json.dumps(tool_results, ensure_ascii=False)}\n\n"
                    "Return ONLY valid JSON in this format:\n"
                    '{"use_tool": false}\n'
                    "or\n"
                    '{"use_tool": true, "tool": "web_search", '
                    '"arguments": {"query": "...", "max_results": 5}}\n\n'
                    "For list_files:\n"
                    '{"use_tool": true, "tool": "list_files", '
                    '"arguments": {}}\n\n'
                    "For read_file:\n"
                    '{"use_tool": true, "tool": "read_file", '
                    '"arguments": {"path": "example.txt"}}'
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


def generate_response(
    client,
    input_text,
    memory,
    plan,
    tool_result=None,
):
    system_content = (
        "You are ChocoJam, a personal second-brain AI agent.\n\n"
        "Answer the user's actual request clearly and directly.\n\n"
        "Use memory only when relevant.\n"
        "Do not add unsolicited recommendations, project advice, "
        "hackathon commentary, or unrelated context.\n"
        "Do not mention internal architecture unless asked.\n"
        "Do not force the user's current project into unrelated answers.\n"
        "Do not invent facts.\n"
        "Clearly distinguish documented facts from inference.\n"
        "If the available evidence does not establish something, "
        "say that it is not established.\n\n"
        f"Memory:\n{json.dumps(memory, ensure_ascii=False)}\n\n"
        f"Execution plan:\n{json.dumps(plan, ensure_ascii=False)}"
    )

    if tool_result is not None:
        system_content += (
            "\n\nTools were executed for this request.\n"
            "Use their results when answering the user.\n"
            "Treat tool results as evidence.\n"
            "Do not invent facts that are not supported by them.\n"
            "When using information from web results, preserve source "
            "titles and URLs so the caller can verify them.\n\n"
            f"Tool results:\n"
            f"{json.dumps(tool_result, ensure_ascii=False)}"
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

    plan = create_task_plan(
        client,
        input_text,
        memory,
    )

    tool_results = []
    tool_used = []
    sources = []
    completed_steps = []

    for step_number in range(3):
        tool_decision = choose_tool(
            client,
            input_text,
            memory,
            plan,
            completed_steps,
            tool_results,
        )

        if tool_decision.get("use_tool") is not True:
            break

        tool_name = tool_decision.get("tool")
        arguments = tool_decision.get("arguments", {})

        try:
            result = execute_tool(
                tool_name,
                **arguments,
            )

            execution_record = {
                "step": step_number + 1,
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            }

            tool_results.append(execution_record)
            tool_used.append(tool_name)

            completed_steps.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                }
            )

            if tool_name == "web_search" and isinstance(result, list):
                sources.extend(
                    [
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                        }
                        for item in result
                        if item.get("url")
                    ]
                )

        except Exception as error:
            tool_results.append(
                {
                    "step": step_number + 1,
                    "tool": tool_name,
                    "arguments": arguments,
                    "error": str(error),
                }
            )
            break

    combined_tool_result = {
        "steps": tool_results
    }

    response_text = generate_response(
        client,
        input_text,
        memory,
        plan,
        combined_tool_result if tool_results else None,
    )

    return {
        "response": response_text,
        "plan": plan,
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