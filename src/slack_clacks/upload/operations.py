"""
Core file upload operations using Slack Web API.
"""

import os

from slack_sdk import WebClient

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".fish": "shell",
    ".pl": "perl",
    ".php": "php",
    ".r": "r",
    ".scala": "scala",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".log": "text",
    ".csv": "csv",
    ".lua": "lua",
    ".zig": "zig",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".dart": "dart",
    ".tf": "terraform",
    ".hcl": "terraform",
    ".dockerfile": "dockerfile",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".diff": "diff",
    ".patch": "diff",
}


FILETYPE_TO_EXTENSION: dict[str, str] = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "go": ".go",
    "rust": ".rs",
    "ruby": ".rb",
    "java": ".java",
    "kotlin": ".kt",
    "c": ".c",
    "cpp": ".cpp",
    "csharp": ".cs",
    "swift": ".swift",
    "shell": ".sh",
    "perl": ".pl",
    "php": ".php",
    "r": ".r",
    "scala": ".scala",
    "sql": ".sql",
    "html": ".html",
    "css": ".css",
    "scss": ".scss",
    "sass": ".sass",
    "less": ".less",
    "xml": ".xml",
    "json": ".json",
    "yaml": ".yaml",
    "toml": ".toml",
    "markdown": ".md",
    "text": ".txt",
    "csv": ".csv",
    "lua": ".lua",
    "zig": ".zig",
    "elixir": ".ex",
    "erlang": ".erl",
    "haskell": ".hs",
    "ocaml": ".ml",
    "clojure": ".clj",
    "dart": ".dart",
    "terraform": ".tf",
    "dockerfile": ".dockerfile",
    "protobuf": ".proto",
    "graphql": ".graphql",
    "diff": ".diff",
    "makefile": ".mk",
}


def filetype_to_extension(filetype: str) -> str:
    """Map a Slack filetype to a file extension. Returns '.txt' if unknown."""
    return FILETYPE_TO_EXTENSION.get(filetype, ".txt")


def infer_filetype(filename: str) -> str:
    """
    Map a filename's extension to a Slack snippet filetype.
    Returns 'text' if the extension is unknown.
    """
    _, ext = os.path.splitext(filename)
    base = os.path.basename(filename).lower()
    if base == "dockerfile":
        return "dockerfile"
    if base == "makefile":
        return "makefile"
    return EXTENSION_MAP.get(ext.lower(), "text")


def upload_file(
    client: WebClient,
    file_path: str,
    filename: str,
    filetype: str | None = None,
    title: str | None = None,
    comment: str | None = None,
    channel_id: str | None = None,
    thread_ts: str | None = None,
) -> dict | bytes:
    """
    Upload a file from disk.
    If channel_id is None, the file is uploaded privately (not shared to any channel).
    Returns a dict with file metadata including 'permalink'.
    """
    kwargs: dict = {
        "file": file_path,
        "filename": filename,
    }
    if filetype:
        kwargs["snippet_type"] = filetype
    if title:
        kwargs["title"] = title
    if comment:
        kwargs["initial_comment"] = comment
    if channel_id:
        kwargs["channel"] = channel_id
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    response = client.files_upload_v2(**kwargs)
    return response.data


def upload_content(
    client: WebClient,
    content: str,
    filename: str,
    filetype: str | None = None,
    title: str | None = None,
    comment: str | None = None,
    channel_id: str | None = None,
    thread_ts: str | None = None,
) -> dict | bytes:
    """
    Upload content string (e.g. from stdin).
    If channel_id is None, the file is uploaded privately (not shared to any channel).
    Returns a dict with file metadata including 'permalink'.
    """
    kwargs: dict = {
        "content": content,
        "filename": filename,
    }
    if filetype:
        kwargs["snippet_type"] = filetype
    if title:
        kwargs["title"] = title
    if comment:
        kwargs["initial_comment"] = comment
    if channel_id:
        kwargs["channel"] = channel_id
    if thread_ts:
        kwargs["thread_ts"] = thread_ts

    response = client.files_upload_v2(**kwargs)
    return response.data
