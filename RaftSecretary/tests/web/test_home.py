from pathlib import Path

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
