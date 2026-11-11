import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.error import HTTPError
from urllib.parse import parse_qs

from slack_sdk import WebClient

from slack_clacks.upload.operations import upload_content, upload_file, upload_types


class UploadServer(ThreadingHTTPServer):
    calls: list[tuple[str, dict[str, str], bytes]]
    upload_status = 200


class UploadHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        server = cast(UploadServer, self.server)
        body = self.rfile.read(int(self.headers["Content-Length"]))
        server.calls.append((self.path, dict(self.headers.items()), body))
        if self.path == "/upload":
            self.send_response(server.upload_status)
            self.end_headers()
            self.wfile.write(b"OK" if server.upload_status == 200 else b"Failed")
            return
        if self.path == "/api/files.getUploadURLExternal":
            result = {
                "ok": True,
                "file_id": "F123",
                "upload_url": f"http://127.0.0.1:{server.server_port}/upload",
            }
        elif self.path == "/api/files.completeUploadExternal":
            result = {"ok": True, "files": [{"id": "F123", "permalink": "test"}]}
        else:
            raise AssertionError(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, format, *args):
        pass


class TestUploadTransport(unittest.TestCase):
    def setUp(self):
        self.server = UploadServer(("127.0.0.1", 0), UploadHandler)
        self.server.calls = []
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = WebClient(
            token="test-token",
            headers={"Cookie": "test-cookie"},
            base_url=f"http://127.0.0.1:{self.server.server_port}/api/",
            retry_handlers=[],
        )
        self.client.proxy = None

    def stop_server(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_binary_files_keep_bytes_and_media_types(self):
        for filename, media_type in [
            ("report.PDF", "application/pdf"),
            ("image.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("animation.gif", "image/gif"),
            ("image.webp", "image/webp"),
            ("drawing.svg", "image/svg+xml"),
            ("archive.zip", "application/zip"),
            ("archive.tar.gz", "application/gzip"),
            (
                "document.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("unknown.unknown-extension", "application/octet-stream"),
        ]:
            with self.subTest(filename=filename):
                self.server.calls.clear()
                path = Path(self.directory.name) / filename
                data = b"\x00\xff\x80\r\nunchanged file bytes"
                path.write_bytes(data)
                result = upload_file(
                    self.client,
                    str(path),
                    filename="renamed-file",
                    title="A document",
                    comment="A comment",
                    channel_id="C123",
                    thread_ts="123.456",
                )
                self.assertEqual(
                    [c[0] for c in self.server.calls],
                    [
                        "/api/files.getUploadURLExternal",
                        "/upload",
                        "/api/files.completeUploadExternal",
                    ],
                )
                allocation = parse_qs(self.server.calls[0][2].decode())
                self.assertNotIn("snippet_type", allocation)
                self.assertEqual(allocation["filename"], ["renamed-file"])
                self.assertEqual(allocation["length"], [str(len(data))])
                headers = {k.lower(): v for k, v in self.server.calls[1][1].items()}
                self.assertEqual(headers["content-type"], media_type)
                self.assertEqual(self.server.calls[1][2], data)
                self.assertNotIn("authorization", headers)
                self.assertNotIn("cookie", headers)
                completion = parse_qs(self.server.calls[2][2].decode())
                self.assertEqual(completion["channel_id"], ["C123"])
                self.assertEqual(completion["thread_ts"], ["123.456"])
                self.assertEqual(completion["initial_comment"], ["A comment"])
                self.assertEqual(
                    json.loads(completion["files"][0]),
                    [{"id": "F123", "title": "A document"}],
                )
                self.assertEqual(result["file"]["id"], "F123")

    def test_explicit_extension_and_media_type(self):
        for override in ["pdf", "application/pdf", "application/vnd.example+binary"]:
            with self.subTest(override=override):
                self.server.calls.clear()
                path = Path(self.directory.name) / "no-extension"
                path.write_bytes(b"%PDF-1.5\n")
                upload_file(self.client, str(path), "report.pdf", filetype=override)
                headers = {k.lower(): v for k, v in self.server.calls[1][1].items()}
                self.assertEqual(
                    headers["content-type"],
                    "application/pdf" if override == "pdf" else override,
                )
                self.assertNotIn(
                    "snippet_type", parse_qs(self.server.calls[0][2].decode())
                )
                self.assertNotIn(
                    "channel_id", parse_qs(self.server.calls[2][2].decode())
                )

    def test_source_file_keeps_snippet_syntax(self):
        path = Path(self.directory.name) / "script.py"
        path.write_text("print('hello')\n")
        upload_file(self.client, str(path), "script.py")
        self.assertEqual(
            parse_qs(self.server.calls[0][2].decode())["snippet_type"], ["python"]
        )
        self.assertEqual(self.server.calls[1][2], path.read_bytes())

    def test_stdin_text_preserves_unicode(self):
        upload_content(self.client, "café\n", "output.txt")
        self.assertEqual(
            parse_qs(self.server.calls[0][2].decode())["snippet_type"], ["text"]
        )
        self.assertEqual(self.server.calls[1][2], "café\n".encode())
        self.assertEqual(self.server.calls[1][1]["Content-Type"], "text/plain")

    def test_failed_byte_upload_is_not_completed(self):
        self.server.upload_status = 500
        with self.assertRaises(HTTPError):
            upload_content(self.client, "example", "test.txt")
        self.assertEqual(
            [c[0] for c in self.server.calls],
            ["/api/files.getUploadURLExternal", "/upload"],
        )

    def test_invalid_type_fails_before_allocating(self):
        for filetype in ["application/pdf\r\nX-Injected: true", "unknown-extension"]:
            with self.subTest(filetype=filetype), self.assertRaises(ValueError):
                upload_content(self.client, "test", "test", filetype=filetype)
        self.assertEqual(self.server.calls, [])


class TestUploadTypes(unittest.TestCase):
    def test_explicit_snippet_syntax(self):
        self.assertEqual(upload_types("file.unknown", "python")[1], "python")

    def test_empty_file_type_uses_filename(self):
        self.assertEqual(upload_types("file.pdf", None), ("application/pdf", None))
