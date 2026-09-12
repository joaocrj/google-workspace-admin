import httpx
import pytest

from google_workspace_admin.reports import user_usage
from google_workspace_admin import server


def _configure_http(monkeypatch, payload: dict) -> dict:
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            captured["raised_for_status"] = True

        def json(self):
            return payload

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params):
            captured["calls"] = captured.get("calls", 0) + 1
            captured["method"] = "GET"
            captured["url"] = url
            captured["headers"] = headers
            captured["params"] = params
            return FakeResponse()

    def fake_get_workspace_access_token(*, scopes):
        captured["scopes"] = scopes
        return "test-value", 3600

    monkeypatch.setattr(user_usage.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        user_usage,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_user_usage_get_uses_endpoint_scope_and_safe_defaults(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "usageReports": [{"date": "2026-09-11"}],
            "nextPageToken": "test-page",
            "warnings": [{"code": "test", "message": "omit"}],
        },
    )

    result = user_usage.get_user_usage_report("2026-09-11")

    assert captured["method"] == "GET"
    assert captured["url"] == user_usage.USER_USAGE_REPORT_URL.format(
        user_key="all",
        date="2026-09-11",
    )
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        user_usage.USER_USAGE_REPORTS_USAGE_READONLY_SCOPE
    ]
    assert captured["params"] == {"maxResults": 25}
    assert "customerId" not in captured["params"]
    assert captured["raised_for_status"] is True
    assert captured["calls"] == 1
    assert result == {
        "usage_reports": [{"date": "2026-09-11"}],
        "next_page_token": "test-page",
        "warnings_present": True,
        "warnings_count": 1,
    }


def test_user_usage_get_encodes_user_key_and_forwards_parameters(monkeypatch):
    captured = _configure_http(monkeypatch, {})

    result = user_usage.get_user_usage_report(
        date="2026-09-11",
        max_results=100,
        page_token="test-page",
        user_key="usage+user@example.com",
        parameters="accounts:disabled, gmail:num_emails_sent",
        filters="accounts:disabled==true",
        org_unit_id="id:org-unit",
    )

    assert captured["url"].endswith(
        "/users/usage%2Buser%40example.com/dates/2026-09-11"
    )
    assert captured["params"] == {
        "maxResults": 100,
        "pageToken": "test-page",
        "parameters": "accounts:disabled, gmail:num_emails_sent",
        "filters": "accounts:disabled==true",
        "orgUnitID": "id:org-unit",
    }
    assert result == {
        "usage_reports": [],
        "next_page_token": None,
        "warnings_present": False,
        "warnings_count": 0,
    }


@pytest.mark.parametrize(
    "date",
    ["2026-9-11", "2026/09/11", "2026-02-29", "2026-09-31", "text"],
)
def test_user_usage_get_rejects_invalid_dates_before_authentication(
    monkeypatch,
    date,
):
    monkeypatch.setattr(
        user_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(ValueError, match="date"):
        user_usage.get_user_usage_report(date)


def test_user_usage_get_requires_date():
    with pytest.raises(TypeError):
        user_usage.get_user_usage_report()  # type: ignore[call-arg]


@pytest.mark.parametrize("max_results", [0, 101])
def test_user_usage_get_rejects_invalid_limits_before_authentication(
    monkeypatch,
    max_results,
):
    monkeypatch.setattr(
        user_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(ValueError, match="max_results deve estar"):
        user_usage.get_user_usage_report(
            "2026-09-11",
            max_results=max_results,
        )


@pytest.mark.parametrize(
    ("parameter_name", "value"),
    [
        ("page_token", " "),
        ("user_key", "\t"),
        ("parameters", ""),
        ("filters", "  "),
        ("org_unit_id", "\t"),
    ],
)
def test_user_usage_get_rejects_blank_strings_before_authentication(
    monkeypatch,
    parameter_name,
    value,
):
    monkeypatch.setattr(
        user_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(
        ValueError,
        match=f"{parameter_name} não pode estar vazio",
    ):
        user_usage.get_user_usage_report(
            "2026-09-11",
            **{parameter_name: value},
        )


def test_user_usage_get_uses_one_page_without_retry(monkeypatch):
    request = httpx.Request(
        "GET",
        user_usage.USER_USAGE_REPORT_URL.format(
            user_key="all",
            date="2026-09-11",
        ),
    )
    response = httpx.Response(403, request=request)
    calls = []

    class FailingResponse:
        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "forbidden",
                request=request,
                response=response,
            )

    class FakeClient:
        def __init__(self, timeout):
            assert timeout == 30.0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def get(self, url, headers, params):
            calls.append((url, params))
            return FailingResponse()

    monkeypatch.setattr(user_usage.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        user_usage,
        "get_workspace_access_token",
        lambda **kwargs: ("test-value", 3600),
    )

    with pytest.raises(httpx.HTTPStatusError) as caught:
        user_usage.get_user_usage_report("2026-09-11")

    assert caught.value.response is response
    assert calls == [
        (
            user_usage.USER_USAGE_REPORT_URL.format(
                user_key="all",
                date="2026-09-11",
            ),
            {"maxResults": 25},
        )
    ]


def test_user_usage_serializer_preserves_safe_identity_and_warnings():
    page = {
        "usage_reports": [
            {
                "kind": "usageReport",
                "etag": "omit-etag",
                "date": "2026-09-11",
                "entity": {
                    "profileId": "profile-123",
                    "userEmail": "omit@example.com",
                    "entityId": "omit-entity",
                    "customerId": "omit-customer",
                },
                "parameters": [
                    {"name": "accounts:disabled", "boolValue": True},
                    {
                        "name": "accounts:drive_used_quota_in_mb",
                        "intValue": 42,
                    },
                    {
                        "name": "accounts:first_name",
                        "stringValue": "omit",
                    },
                    {"name": "accounts:unknown", "intValue": 9},
                    {
                        "name": "accounts:disabled",
                        "msgValue": {"parameter": []},
                    },
                ],
            }
        ],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 2,
    }

    result = server._serialize_user_usage_page(
        page,
        parameters="accounts:disabled,accounts:drive_used_quota_in_mb",
    )

    assert result == {
        "usage_reports": [
            {
                "date": "2026-09-11",
                "profile_id": "profile-123",
                "parameters": [
                    {
                        "parameter_name": "accounts:disabled",
                        "boolean_value": True,
                    },
                    {
                        "parameter_name": "accounts:drive_used_quota_in_mb",
                        "integer_value": 42,
                    },
                ],
            }
        ],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 2,
    }
    assert "userEmail" not in str(result)
    assert "entityId" not in str(result)
    assert "customerId" not in str(result)
    assert "payload" not in result


def test_user_usage_serializer_uses_current_timestamp_name_only_when_requested():
    report = {
        "date": "2026-09-11",
        "entity": {"profileId": "profile-123"},
        "parameters": [
            {
                "name": "accounts:timestamp_creation",
                "datetimeValue": "2020-01-01T00:00:00.000Z",
            },
            {
                "name": "accounts:timestamp_last_login",
                "datetimeValue": "2026-09-10T00:00:00.000Z",
            },
            {
                "name": "accounts:timestamp_last_sso",
                "datetimeValue": "2026-09-09T00:00:00.000Z",
            },
            {
                "name": "accounts:last_login_time",
                "datetimeValue": "omit-old-name",
            },
        ],
    }

    not_requested = server._serialize_user_usage_report(
        report,
        requested_parameters=set(),
    )
    assert not_requested["parameters"] == []

    requested = server._serialize_user_usage_report(
        report,
        requested_parameters={
            "accounts:timestamp_last_login",
            "accounts:timestamp_last_sso",
        },
    )
    assert requested["parameters"] == [
        {
            "parameter_name": "accounts:timestamp_last_login",
            "datetime_value": "2026-09-10T00:00:00.000Z",
        },
        {
            "parameter_name": "accounts:timestamp_last_sso",
            "datetime_value": "2026-09-09T00:00:00.000Z",
        },
    ]


def test_user_usage_serializer_allows_safe_other_groups_and_omits_strings():
    report = {
        "date": "2026-09-11",
        "entity": {"profileId": "profile-123"},
        "parameters": [
            {
                "name": "docs:num_docs",
                "intValue": 3,
            },
            {
                "name": "gmail:num_emails_sent",
                "intValue": 4,
            },
            {
                "name": "chat:num_28day_spaces_created",
                "intValue": 5,
            },
            {
                "name": "classroom:num_courses_created",
                "intValue": 6,
            },
            {
                "name": "classroom:role",
                "stringValue": "teacher",
            },
            {
                "name": "accounts:unknown_id",
                "stringValue": "opaque",
            },
        ],
    }

    result = server._serialize_user_usage_report(
        report,
        requested_parameters=set(),
    )

    assert result["parameters"] == [
        {"parameter_name": "docs:num_docs", "integer_value": 3},
        {"parameter_name": "gmail:num_emails_sent", "integer_value": 4},
        {
            "parameter_name": "chat:num_28day_spaces_created",
            "integer_value": 5,
        },
        {
            "parameter_name": "classroom:num_courses_created",
            "integer_value": 6,
        },
    ]
    assert "string_value" not in str(result)
    assert "msgValue" not in str(result)
