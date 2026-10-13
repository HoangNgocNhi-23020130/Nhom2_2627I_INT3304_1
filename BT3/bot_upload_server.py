#!/usr/bin/env python3
"""HTTP endpoint for receiving bot source files into the bots directory."""

import json
import os
import re
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT_DIR = Path(__file__).resolve().parent
BOTS_DIR = ROOT_DIR / "bots"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_EXTENSIONS = {".py", ".cpp", ".js"}
DEFAULT_ALLOWED_ORIGINS = {
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "https://hoangngocnhi-23020130.github.io",
}


def get_allowed_origins():
    configured_origins = os.environ.get("BOT_UPLOAD_ALLOWED_ORIGINS")
    if configured_origins is None:
        return DEFAULT_ALLOWED_ORIGINS
    return {origin.strip() for origin in configured_origins.split(",") if origin.strip()}


class BotUploadHandler(BaseHTTPRequestHandler):
    server_version = "BotUploadServer/1.0"

    def _send_json(self, status, payload, origin=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _check_origin(self):
        origin = self.headers.get("Origin")
        if origin and origin not in get_allowed_origins():
            self._send_json(403, {"error": "Origin không được phép tải bot lên."})
            return None
        return origin

    def do_OPTIONS(self):
        if urlsplit(self.path).path != "/api/bots/upload":
            self._send_json(404, {"error": "Không tìm thấy endpoint."})
            return

        origin = self._check_origin()
        if self.headers.get("Origin") and origin is None:
            return

        self.send_response(204)
        self.send_header("Allow", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
        self.end_headers()

    def do_POST(self):
        if urlsplit(self.path).path != "/api/bots/upload":
            self._send_json(404, {"error": "Không tìm thấy endpoint."})
            return

        origin = self._check_origin()
        if self.headers.get("Origin") and origin is None:
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_json(400, {"error": "Content-Length không hợp lệ."}, origin)
            return
        if content_length <= 0:
            self._send_json(400, {"error": "File tải lên đang trống."}, origin)
            return
        if content_length > MAX_UPLOAD_BYTES:
            self._send_json(413, {"error": "Dung lượng file tối đa là 2 MB."}, origin)
            return

        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data;"):
            self._send_json(400, {"error": "Yêu cầu phải dùng multipart/form-data."}, origin)
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self._send_json(400, {"error": "Dữ liệu tải lên không đầy đủ."}, origin)
            return

        try:
            mime_message = BytesParser(policy=policy.default).parsebytes(
                b"Content-Type: "
                + content_type.encode("ascii")
                + b"\r\nMIME-Version: 1.0\r\n\r\n"
                + body
            )
        except (UnicodeEncodeError, ValueError):
            self._send_json(400, {"error": "Định dạng dữ liệu tải lên không hợp lệ."}, origin)
            return

        if not mime_message.is_multipart():
            self._send_json(400, {"error": "Không đọc được file tải lên."}, origin)
            return

        parts = list(mime_message.iter_parts())
        file_parts = [
            part for part in parts
            if part.get_param("name", header="content-disposition") == "botFile"
        ]
        if len(parts) != 1 or len(file_parts) != 1:
            self._send_json(400, {"error": "Yêu cầu chỉ chứa một file bot."}, origin)
            return

        file_part = file_parts[0]
        filename = file_part.get_filename()
        if not filename or filename != Path(filename).name or any(
            char in filename for char in ("/", "\\", "\0")
        ):
            self._send_json(400, {"error": "Tên file không hợp lệ."}, origin)
            return
        if len(filename) > 100 or any(ord(char) < 32 for char in filename):
            self._send_json(400, {"error": "Tên file không hợp lệ."}, origin)
            return

        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            self._send_json(400, {"error": "Chỉ chấp nhận file .py, .cpp hoặc .js."}, origin)
            return

        file_content = file_part.get_payload(decode=True)
        if not file_content:
            self._send_json(400, {"error": "File tải lên đang trống."}, origin)
            return
        if len(file_content) > MAX_UPLOAD_BYTES:
            self._send_json(413, {"error": "Dung lượng file tối đa là 2 MB."}, origin)
            return

        BOTS_DIR.mkdir(parents=True, exist_ok=True)
        destination = BOTS_DIR / filename
        try:
            with destination.open("xb") as uploaded_file:
                uploaded_file.write(file_content)
        except FileExistsError:
            self._send_json(409, {"error": "Đã có bot trùng tên trong thư mục bots."}, origin)
            return
        except OSError:
            self.log_error("Could not save uploaded bot file")
            self._send_json(500, {"error": "Không thể lưu file vào thư mục bots."}, origin)
            return

        self._send_json(
            201,
            {"message": "Tải bot lên thành công.", "filename": filename},
            origin,
        )


def main():
    host = os.environ.get("BOT_UPLOAD_HOST", "127.0.0.1")
    port = int(os.environ.get("BOT_UPLOAD_PORT", "8081"))
    server = ThreadingHTTPServer((host, port), BotUploadHandler)
    print(f"Bot upload API đang chạy tại http://{host}:{port}")
    print(f"Bot được lưu vào: {BOTS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang dừng Bot upload API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
