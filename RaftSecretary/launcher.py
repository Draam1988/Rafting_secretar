from __future__ import annotations

import sys
import threading
import webbrowser
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

import tkinter as tk
from tkinter import messagebox

from raftsecretary.web.app import create_app


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
DATA_DIR = BASE_DIR / "data"
HOST = "127.0.0.1"
PORT = 8000


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


class LauncherApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("RaftSecretary")
        self.root.geometry("460x220")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.server = None
        self.server_thread: threading.Thread | None = None
        self.status_var = tk.StringVar(value="Подготовка запуска...")
        self.url = f"http://{HOST}:{PORT}"
        self._build_ui()

    def _build_ui(self) -> None:
        frame = tk.Frame(self.root, padx=18, pady=18)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="RaftSecretary",
            font=("Georgia", 24, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            frame,
            text="Прототип для тестирования на Windows",
            font=("Georgia", 11),
            anchor="w",
        ).pack(fill="x", pady=(4, 14))

        tk.Label(
            frame,
            textvariable=self.status_var,
            justify="left",
            anchor="w",
            wraplength=400,
        ).pack(fill="x")

        buttons = tk.Frame(frame, pady=18)
        buttons.pack(fill="x")
        tk.Button(buttons, text="Открыть в браузере", width=18, command=self._open_browser).pack(side="left")
        tk.Button(buttons, text="Закрыть приложение", width=18, command=self._close).pack(side="right")

    def _open_browser(self) -> None:
        webbrowser.open(self.url)

    def _start_server(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        app = create_app(DATA_DIR)

        def wsgi_app(environ, start_response):  # type: ignore[no-untyped-def]
            method = environ["REQUEST_METHOD"]
            path = build_request_path(environ)
            form_data = None
            if method == "POST":
                form_data = parse_post_form_data(environ)
            status, headers, body = app.handle(method, path, form_data=form_data)
            start_response(status, headers)
            return [body.encode("utf-8")]

        try:
            self.server = make_server(HOST, PORT, wsgi_app)
        except OSError as error:
            self.status_var.set(
                "Не удалось запустить сервер.\n"
                f"Порт {PORT} уже занят или недоступен.\n{error}"
            )
            return

        self.status_var.set(
            "Сервер запущен.\n"
            f"Адрес: {self.url}\n"
            "Браузер откроется автоматически."
        )
        self._open_browser()
        self.server.serve_forever()

    def run(self) -> None:
        self.server_thread = threading.Thread(target=self._start_server, daemon=True)
        self.server_thread.start()
        self.root.mainloop()

    def _close(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        self.root.destroy()


if __name__ == "__main__":
    try:
        LauncherApp().run()
    except Exception as error:  # pragma: no cover
        messagebox.showerror("RaftSecretary", f"Ошибка запуска:\n{error}")
