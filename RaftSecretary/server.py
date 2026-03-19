from __future__ import annotations

from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from raftsecretary.web.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"


def build_request_path(environ: dict[str, str]) -> str:
    path = environ["PATH_INFO"]
    query_string = environ.get("QUERY_STRING", "")
    if query_string:
        return f"{path}?{query_string}"
    return path


def parse_post_form_data(environ: dict[str, object]) -> dict[str, str]:
    content_type = str(environ.get("CONTENT_TYPE") or "")
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    raw_body = environ["wsgi.input"].read(content_length)  # type: ignore[index]
    if content_type.startswith("multipart/form-data"):
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            + raw_body
        )
        parsed: dict[str, str] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            payload = part.get_payload(decode=True)
            parsed[name] = payload.decode("utf-8") if isinstance(payload, bytes) else str(part.get_content())
        return parsed

    parsed = parse_qs(raw_body.decode("utf-8"))
    return {key: values[0] for key, values in parsed.items()}


def main() -> None:
    app = create_app(DATA_DIR)

    def wsgi_app(environ, start_response):  # type: ignore[no-untyped-def]
        method = environ["REQUEST_METHOD"]
        path = build_request_path(environ)
        form_data = None

        if method == "POST":
            form_data = parse_post_form_data(environ)

        try:
            status, headers, body = app.handle(method, path, form_data=form_data)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            error_html = f"<pre>Ошибка экспорта:\n{traceback.format_exc()}</pre>".encode("utf-8")
            start_response("500 Internal Server Error", [("Content-Type", "text/html; charset=utf-8")])
            return [error_html]
        start_response(status, headers)
        return [body if isinstance(body, bytes) else body.encode("utf-8")]

    host = "127.0.0.1"
    port = 8000
    print(f"RaftSecretary running at http://{host}:{port}")
    with make_server(host, port, wsgi_app) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
