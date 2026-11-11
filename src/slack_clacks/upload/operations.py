"""
Core file upload operations using Slack Web API.
"""

import mimetypes
import os
import re
from pathlib import Path
from urllib.request import (
    BaseHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

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


def infer_filetype(filename: str) -> str | None:
    """
    Map a filename's extension to a Slack snippet filetype.
    Returns None for files without a known snippet syntax.
    """
    _, ext = os.path.splitext(filename)
    base = os.path.basename(filename).lower()
    if base == "dockerfile":
        return "dockerfile"
    if base == "makefile":
        return "makefile"
    return EXTENSION_MAP.get(ext.lower())


def media_type_for_filename(filename: str) -> str | None:
    media_type, encoding = mimetypes.guess_file_type(filename, strict=False)
    if encoding:
        return {
            "gzip": "application/gzip",
            "bzip2": "application/x-bzip2",
            "xz": "application/x-xz",
            "compress": "application/x-compress",
            "br": "application/brotli",
            "zstd": "application/zstd",
        }[encoding]
    return media_type


def upload_types(filename: str, filetype: str | None) -> tuple[str, str | None]:
    """Keep Slack snippet syntax separate from the file's HTTP media type."""
    if filetype and "/" in filetype:
        token = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
        if not re.fullmatch(token + "/" + token, filetype):
            raise ValueError(f"Invalid media type: {filetype!r}")
        return filetype, None
    if filetype and filetype not in FILETYPE_TO_EXTENSION:
        media_type = media_type_for_filename("file." + filetype.lstrip("."))
        if media_type is None:
            raise ValueError(
                f"Unknown file type: {filetype!r}; "
                "use a media type such as application/pdf"
            )
        return media_type, None
    snippet_type = filetype or infer_filetype(filename)
    type_filename = "file" + FILETYPE_TO_EXTENSION[filetype] if filetype else filename
    media_type = media_type_for_filename(type_filename)
    return media_type or (
        "text/plain" if snippet_type else "application/octet-stream"
    ), snippet_type


def upload_bytes(
    client: WebClient,
    data: bytes,
    filename: str,
    media_type: str,
    snippet_type: str | None,
    title: str | None,
    comment: str | None,
    channel_id: str | None,
    thread_ts: str | None,
) -> dict | bytes:
    allocation = client.files_getUploadURLExternal(
        filename=filename, length=len(data), snippet_type=snippet_type
    )
    request = Request(
        allocation["upload_url"],
        data=data,
        headers={"Content-Type": media_type},
        method="POST",
    )
    # The SDK's byte-upload helper omits Content-Type. Send it explicitly,
    # without copying Slack API authentication headers to the upload URL.
    handlers: list[BaseHandler] = [HTTPSHandler(context=client.ssl)]
    if client.proxy:
        handlers.append(ProxyHandler({"http": client.proxy, "https": client.proxy}))
    opener = build_opener(*handlers)
    with opener.open(request, timeout=client.timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"File upload failed with HTTP {response.status}")
        response.read()
    result = client.files_completeUploadExternal(
        files=[{"id": allocation["file_id"], "title": title or filename}],
        channel_id=channel_id,
        initial_comment=comment,
        thread_ts=thread_ts,
    ).data
    if isinstance(result, dict) and len(result.get("files", [])) == 1:
        result["file"] = result["files"][0]
    return result


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
    """Upload a file unchanged; no channel means a private upload."""
    media_type, snippet_type = upload_types(file_path, filetype)
    return upload_bytes(
        client,
        Path(file_path).read_bytes(),
        filename,
        media_type,
        snippet_type,
        title,
        comment,
        channel_id,
        thread_ts,
    )


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
    """Upload text from stdin; no channel means a private upload."""
    media_type, snippet_type = upload_types(filename, filetype or "text")
    return upload_bytes(
        client,
        content.encode("utf-8"),
        filename,
        media_type,
        snippet_type,
        title,
        comment,
        channel_id,
        thread_ts,
    )
