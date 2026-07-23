from __future__ import annotations

import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .api import ApiApplication


def make_handler(application: ApiApplication) -> type[BaseHTTPRequestHandler]:
    class ApiHandler(BaseHTTPRequestHandler):
        server_version = "NoticeApi/2.1"

        def do_GET(self) -> None:
            self._respond("GET")

        def do_HEAD(self) -> None:
            self._respond("HEAD")

        def do_POST(self) -> None:
            self._respond("POST")

        def do_PUT(self) -> None:
            self._respond("PUT")

        def do_DELETE(self) -> None:
            self._respond("DELETE")

        def _respond(self, method: str) -> None:
            response = application.dispatch(method, self.path)
            body = response.body()
            self.send_response(response.status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Allow", "GET, HEAD")
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            logging.info("%s - %s", self.address_string(), format % args)

    return ApiHandler


def serve(application: ApiApplication, host: str, port: int) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(application))
    logging.info("API listening on http://%s:%s", host, server.server_port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
