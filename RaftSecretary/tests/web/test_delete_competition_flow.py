from pathlib import Path

from raftsecretary.storage.db import create_competition_db
from raftsecretary.web.app import create_app


def test_delete_confirmation_page_shows_human_name_without_db_extension(tmp_path: Path) -> None:
    create_competition_db(tmp_path / "Первенство_КК.db")
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/competitions/delete?db=%D0%9F%D0%B5%D1%80%D0%B2%D0%B5%D0%BD%D1%81%D1%82%D0%B2%D0%BE_%D0%9A%D0%9A.db")

    assert status == "200 OK"
    assert "Удалить соревнование" in body
    assert "Первенство_КК" in body
    assert "Удалить соревнование <strong>Первенство_КК</strong>" in body


def test_delete_competition_endpoint_removes_db_file_and_redirects_home(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/competitions/delete",
        form_data={"db": "test.db", "confirm": "yes"},
    )

    assert status == "303 See Other"
    assert ("Location", "/") in headers
    assert body == ""
    assert not db_path.exists()
