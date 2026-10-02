from tools.web_search import web_search


TOOLS = {
    "web_search": web_search,
}


def get_tool(name: str):
    return TOOLS.get(name)


def list_tools():
    return list(TOOLS.keys())