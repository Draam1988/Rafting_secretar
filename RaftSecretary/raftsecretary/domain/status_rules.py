STATUS_OK = "OK"
STATUS_DID_NOT_FINISH = "Н/ФИН"
STATUS_DID_NOT_START = "Н/СТ"
STATUS_DISQUALIFIED_ATTEMPT = "ДИСКВ/П"
STATUS_DISQUALIFIED_SERIES = "ДИСКВ/С"
STATUS_RETIRED = "СХОД"  # voluntary withdrawal mid-race


def place_value_for_status(status: str, place: int, starters_count: int) -> int | None:
    if status == STATUS_OK:
        return place
    if status in {STATUS_DID_NOT_FINISH, STATUS_DISQUALIFIED_ATTEMPT}:
        return starters_count
    if status in {STATUS_DID_NOT_START, STATUS_DISQUALIFIED_SERIES, STATUS_RETIRED}:
        return None
    raise ValueError(f"Unsupported status: {status}")

