from __future__ import annotations

import datetime
import traceback as tb
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from raftsecretary.web.app import create_app


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_FILE = PROJECT_ROOT / "errors.log"


def build_request_path(environ: dict[str, str]) -> str:
    path = environ["PATH_INFO"]
    query_string = environ.get("QUERY_STRING", "")
    if query_string:
        return f"{path}?{query_string}"
    return path


def parse_post_form_data(environ: dict[str, object]) -> dict[str, str | bytes]:
    content_type = str(environ.get("CONTENT_TYPE") or "")
    content_length = int(environ.get("CONTENT_LENGTH") or 0)
    raw_body = environ["wsgi.input"].read(content_length)  # type: ignore[index]
    if content_type.startswith("multipart/form-data"):
        message = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8")
            + raw_body
        )
        parsed: dict[str, str | bytes] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            payload = part.get_payload(decode=True)
            filename = part.get_param("filename", header="content-disposition")
            if filename and isinstance(payload, bytes):
                # file upload — keep raw bytes, store filename under "<name>__filename"
                parsed[name] = payload
                parsed[f"{name}__filename"] = filename
            elif isinstance(payload, bytes):
                parsed[name] = payload.decode("utf-8", errors="replace")
            else:
                parsed[name] = str(part.get_content())
        return parsed

    parsed_qs = parse_qs(raw_body.decode("utf-8"))
    return {key: values[0] for key, values in parsed_qs.items()}


def _write_error_log(method: str, path: str, error_text: str) -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"[{timestamp}]  {method}  {path}\n")
            f.write(error_text)
            f.write("\n")
    except OSError:
        pass  # если не можем писать лог — молча продолжаем


def main() -> None:
    app = create_app(DATA_DIR, log_file=LOG_FILE)

    def wsgi_app(environ, start_response):  # type: ignore[no-untyped-def]
        method = environ["REQUEST_METHOD"]
        path = build_request_path(environ)
        form_data = None

        if method == "POST":
            form_data = parse_post_form_data(environ)

        try:
            status, headers, body = app.handle(method, path, form_data=form_data)
        except Exception:
            error_text = tb.format_exc()
            _write_error_log(method, path, error_text)
            error_html = f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>Ошибка</title>
<style>
  body {{ font-family: Georgia, serif; background: #fbf9f3; color: #31332b;
         max-width: 700px; margin: 80px auto; padding: 0 24px; }}
  h1 {{ font-size: 28px; color: #9e422c; border-bottom: 2px solid #9e422c;
        padding-bottom: 12px; }}
  .path {{ background: #efeee5; padding: 12px 16px; font-family: monospace;
           font-size: 13px; word-break: break-all; margin: 20px 0; }}
  p {{ line-height: 1.7; }}
  a {{ color: #386948; }}
</style></head>
<body>
  <h1>Произошла ошибка</h1>
  <p>RaftSecretary столкнулся с непредвиденной ошибкой при обработке запроса.</p>
  <p>Ошибка записана в файл:</p>
  <div class="path">{LOG_FILE}</div>
  <p>Пожалуйста, <strong>отправьте этот файл автору программы</strong> для анализа.</p>
  <p><a href="/">← Вернуться на главную</a></p>
</body></html>""".encode("utf-8")
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
