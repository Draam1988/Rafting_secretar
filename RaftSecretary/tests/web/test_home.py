import sqlite3
from pathlib import Path

from raftsecretary.storage.db import create_competition_db
from raftsecretary.web.app import create_app


def test_home_page_lists_existing_competition_files(tmp_path: Path) -> None:
    (tmp_path / "alpha.db").write_text("", encoding="utf-8")
    (tmp_path / "beta.db").write_text("", encoding="utf-8")
    app = create_app(tmp_path)

    status, headers, body = app.handle("GET", "/")

    assert status == "200 OK"
    assert ("Content-Type", "text/html; charset=utf-8") in headers
    assert "alpha.db" in body
    assert "beta.db" in body


def test_create_competition_endpoint_creates_db_file(tmp_path: Path) -> None:
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/competitions",
        form_data={"filename": "moscow_2026"},
    )

    assert status == "303 See Other"
    assert ("Location", "/dashboard?db=moscow_2026.db") in headers
    assert body == ""
    assert (tmp_path / "moscow_2026.db").exists()


def test_create_competition_redirect_escapes_unicode_filename_for_location_header(tmp_path: Path) -> None:
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/competitions",
        form_data={"filename": "ЮФО"},
    )

    assert status == "303 See Other"
    assert ("Location", "/dashboard?db=%D0%AE%D0%A4%D0%9E.db") in headers
    assert body == ""
    assert (tmp_path / "ЮФО.db").exists()


def test_download_competition_uses_attachment_header_safe_for_unicode_filename(tmp_path: Path) -> None:
    create_competition_db(tmp_path / "ЮФО.db")
    app = create_app(tmp_path)

    status, headers, body = app.handle("GET", "/competitions/download?db=%D0%AE%D0%A4%D0%9E.db")

    headers_map = dict(headers)

    assert status == "200 OK"
    assert headers_map["Content-Type"] == "application/octet-stream"
    assert 'attachment;' in headers_map["Content-Disposition"]
    assert 'filename="competition.db"' in headers_map["Content-Disposition"]
    assert "filename*=UTF-8''%D0%AE%D0%A4%D0%9E.db" in headers_map["Content-Disposition"]
    assert isinstance(body, bytes)


def test_import_rejects_database_from_newer_schema_version(tmp_path: Path) -> None:
    source_db = tmp_path / "future.db"
    create_competition_db(source_db)
    with sqlite3.connect(source_db) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO app_meta (key, value) VALUES ('schema_version', '999')"
        )
        connection.commit()
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/competitions/import",
        form_data={
            "db_file": source_db.read_bytes(),
            "db_file__filename": "future.db",
        },
    )

    assert status == "303 See Other"
    assert ("Location", "/?import_error=incompatible") in headers
    assert body == ""


def test_home_page_shows_import_error_for_incompatible_version(tmp_path: Path) -> None:
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/?import_error=incompatible")

    assert status == "200 OK"
    assert "более новой версии" in body
