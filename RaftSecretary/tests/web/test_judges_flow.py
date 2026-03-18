from pathlib import Path

from raftsecretary.storage.db import create_competition_db
from raftsecretary.storage.judges_storage import load_judges
from raftsecretary.web.app import create_app


def test_judges_page_shows_required_roles_and_add_button(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, _, body = app.handle("GET", "/judges?db=event.db")

    assert status == "200 OK"
    assert "Главный судья соревнований" in body
    assert "Главный секретарь соревнований" in body
    assert "Начальник дистанции" in body
    assert "Добавить судью" in body
    assert "Спортивный судья всероссийской категории" in body


def test_save_judges_endpoint_persists_required_roles_and_judges(tmp_path: Path) -> None:
    db_path = tmp_path / "event.db"
    create_competition_db(db_path)
    app = create_app(tmp_path)

    status, headers, body = app.handle(
        "POST",
        "/judges/save",
        form_data={
            "db": "event.db",
            "chief_judge_last_name": "Иванов",
            "chief_judge_first_name": "Иван",
            "chief_judge_patronymic": "Иванович",
            "chief_judge_category": "Спортивный судья всероссийской категории",
            "chief_secretary_last_name": "Петрова",
            "chief_secretary_first_name": "Анна",
            "chief_secretary_patronymic": "Сергеевна",
            "chief_secretary_category": "Спортивный судья первой категории",
            "course_chief_last_name": "Сидоров",
            "course_chief_first_name": "Павел",
            "course_chief_patronymic": "Олегович",
            "course_chief_category": "Спортивный судья второй категории",
            "judge_1_last_name": "Кузнецов",
            "judge_1_first_name": "Дмитрий",
            "judge_1_patronymic": "Андреевич",
            "judge_1_category": "Спортивный судья третьей категории",
            "judge_2_last_name": "Орлова",
            "judge_2_first_name": "Мария",
            "judge_2_patronymic": "Игоревна",
            "judge_2_category": "Юный спортивный судья",
        },
    )

    saved = load_judges(db_path)

    assert status == "303 See Other"
    assert ("Location", "/judges?db=event.db") in headers
    assert body == ""
    assert saved.chief_judge.last_name == "Иванов"
    assert saved.chief_secretary.last_name == "Петрова"
    assert saved.course_chief.last_name == "Сидоров"
    assert [judge.last_name for judge in saved.judges] == ["Кузнецов", "Орлова"]
