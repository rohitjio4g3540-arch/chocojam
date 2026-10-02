import json
import os


MEMORY_DIR = os.path.dirname(__file__)


def _get_path(filename):
    return os.path.join(MEMORY_DIR, filename)


def load_memory(filename):
    path = _get_path(filename)

    if not os.path.exists(path):
        return {}

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(filename, data):
    path = _get_path(filename)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def update_memory(filename, key, value):
    data = load_memory(filename)
    data[key] = value
    save_memory(filename, data)
    return data


def get_profile():
    return load_memory("profile.json")


def update_profile(key, value):
    return update_memory("profile.json", key, value)


def get_projects():
    return load_memory("projects.json")


def update_project(key, value):
    return update_memory("projects.json", key, value)


def get_knowledge():
    return load_memory("knowledge.json")


def update_knowledge(key, value):
    return update_memory("knowledge.json", key, value)


def get_conversations():
    return load_memory("conversations.json")


def update_conversations(key, value):
    return update_memory("conversations.json", key, value)