from io import BytesIO

from server import build_request_path, parse_post_form_data


def test_build_request_path_includes_query_string() -> None:
    environ = {
        "PATH_INFO": "/dashboard",
        "QUERY_STRING": "db=%D1%82%D0%B5%D1%81%D1%82.db",
    }

    assert build_request_path(environ) == "/dashboard?db=%D1%82%D0%B5%D1%81%D1%82.db"


def test_parse_post_form_data_supports_urlencoded_body() -> None:
    body = b"db=event.db&category_key=R4%3Amen%3AU16&team_name=%D0%A8%D1%82%D0%BE%D1%80%D0%BC"
    environ = {
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
        "wsgi.input": BytesIO(body),
    }

    parsed = parse_post_form_data(environ)

    assert parsed == {
        "db": "event.db",
        "category_key": "R4:men:U16",
        "team_name": "Шторм",
    }


def test_parse_post_form_data_supports_multipart_form_data() -> None:
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="db"\r\n\r\n'
        "event.db\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="category_key"\r\n\r\n'
        "R4:men:U16\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="team_name"\r\n\r\n'
        "Шторм\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    environ = {
        "REQUEST_METHOD": "POST",
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": f"multipart/form-data; boundary={boundary}",
        "wsgi.input": BytesIO(body),
    }

    parsed = parse_post_form_data(environ)

    assert parsed == {
        "db": "event.db",
        "category_key": "R4:men:U16",
        "team_name": "Шторм",
    }
