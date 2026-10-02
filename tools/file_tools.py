import os


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


def _safe_path(relative_path: str):
    path = os.path.abspath(
        os.path.join(PROJECT_ROOT, relative_path)
    )

    if not path.startswith(PROJECT_ROOT):
        raise ValueError("Path is outside the ChocoJam project")

    return path


def list_files():
    files = []

    for root, directories, filenames in os.walk(PROJECT_ROOT):
        directories[:] = [
            directory
            for directory in directories
            if directory not in {
                ".git",
                "__pycache__",
                ".venv",
                "venv",
            }
        ]

        for filename in filenames:
            full_path = os.path.join(root, filename)

            relative_path = os.path.relpath(
                full_path,
                PROJECT_ROOT,
            )

            files.append(
                relative_path.replace("\\", "/")
            )

    return sorted(files)


def read_file(path: str):
    safe_path = _safe_path(path)

    if not os.path.isfile(safe_path):
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with open(
        safe_path,
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()