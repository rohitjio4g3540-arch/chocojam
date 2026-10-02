from tools.web_search import web_search


TOOLS = {
    "web_search": web_search,
}


def get_tool(name: str):
    return TOOLS.get(name)


def list_tools():
    return list(TOOLS.keys())


def execute_tool(name: str, **kwargs):
    tool = get_tool(name)

    if tool is None:
        raise ValueError(f"Unknown tool: {name}")

    return tool(**kwargs)