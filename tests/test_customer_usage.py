import httpx
import pytest

from google_workspace_admin.reports import customer_usage
from google_workspace_admin import server


VALID_PARAMETERS = "accounts:num_users"


def test_customer_usage_allowlist_is_exact():
    assert customer_usage.CUSTOMER_USAGE_ALLOWED_PARAMETERS == frozenset(
        {
            "accounts:num_users",
            "accounts:num_archived_users",
            "accounts:num_disabled_accounts",
            "accounts:num_suspended_users",
            "accounts:customer_used_quota_in_mb",
            "accounts:drive_used_quota_in_mb",
            "accounts:gmail_used_quota_in_mb",
            "accounts:team_drive_used_quota_in_mb",
            "accounts:total_quota_in_mb",
            "accounts:used_quota_in_mb",
        }
    )


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

    monkeypatch.setattr(customer_usage.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        customer_usage,
        "get_workspace_access_token",
        fake_get_workspace_access_token,
    )

    return captured


def test_customer_usage_get_uses_endpoint_scope_and_safe_defaults(monkeypatch):
    captured = _configure_http(
        monkeypatch,
        {
            "usageReports": [{"date": "2026-09-10"}],
            "nextPageToken": "next-page",
            "warnings": [{"code": "omit", "message": "omit"}],
        },
    )

    result = customer_usage.get_customer_usage_report(
        "2026-09-10",
        VALID_PARAMETERS,
    )

    assert captured["method"] == "GET"
    assert captured["url"] == customer_usage.CUSTOMER_USAGE_REPORT_URL.format(
        date="2026-09-10",
    )
    assert captured["params"] == {"parameters": VALID_PARAMETERS}
    assert "customerId" not in captured["params"]
    assert "maxResults" not in captured["params"]
    assert captured["timeout"] == 30.0
    assert captured["scopes"] == [
        customer_usage.CUSTOMER_USAGE_REPORTS_USAGE_READONLY_SCOPE
    ]
    assert captured["raised_for_status"] is True
    assert captured["calls"] == 1
    assert result == {
        "usage_reports": [{"date": "2026-09-10"}],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 1,
    }


def test_customer_usage_get_normalizes_parameter_spaces_and_preserves_order(
    monkeypatch,
):
    captured = _configure_http(monkeypatch, {})

    result = customer_usage.get_customer_usage_report(
        date="2026-09-10",
        parameters=(
            " accounts:used_quota_in_mb, "
            "accounts:num_users,accounts:total_quota_in_mb "
        ),
        page_token="next-page",
    )

    assert captured["params"] == {
        "parameters": (
            "accounts:used_quota_in_mb,accounts:num_users,"
            "accounts:total_quota_in_mb"
        ),
        "pageToken": "next-page",
    }
    assert result["next_page_token"] is None


@pytest.mark.parametrize(
    "date",
    ["2026-9-10", "2026/09/10", "2026-02-29", "2026-09-31", "text"],
)
def test_customer_usage_get_rejects_invalid_dates_before_authentication(
    monkeypatch,
    date,
):
    monkeypatch.setattr(
        customer_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(ValueError, match="date"):
        customer_usage.get_customer_usage_report(date, VALID_PARAMETERS)


def test_customer_usage_get_requires_date_and_parameters():
    with pytest.raises(TypeError):
        customer_usage.get_customer_usage_report()  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        customer_usage.get_customer_usage_report("2026-09-10")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "parameters",
    [
        None,
        "",
        " ",
        "accounts:num_users,",
        ",accounts:num_users",
        "accounts:num_users,,accounts:used_quota_in_mb",
        "accounts:num_users, accounts:num_users",
        "accounts:num_users,accounts:unknown",
        "accounts:num_locked_users",
        "accounts:num_super_admins",
        "accounts:num_delegated_admins",
        "accounts:all_domain_names",
        "accounts:num_passkeys_enrolled",
        "accounts:num_security_keys",
        "accounts:num_users_2sv_enforced",
        "accounts:password_strength",
        "all",
        "*",
        "accounts",
        "gmail:num_users",
        "calendar:num_events",
        "cros:num_devices",
        "gplus:num_users",
        "app_maker:num_users",
        "apps_scripts:num_users",
        "device_management:num_devices",
        "meet:num_calls",
    ],
)
def test_customer_usage_get_rejects_invalid_parameters_before_authentication(
    monkeypatch,
    parameters,
):
    monkeypatch.setattr(
        customer_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(ValueError, match="parameters"):
        customer_usage.get_customer_usage_report("2026-09-10", parameters)


def test_customer_usage_get_rejects_blank_page_token_before_authentication(
    monkeypatch,
):
    monkeypatch.setattr(
        customer_usage,
        "get_workspace_access_token",
        lambda **kwargs: pytest.fail("A autenticação não deveria ocorrer."),
    )

    with pytest.raises(ValueError, match="page_token"):
        customer_usage.get_customer_usage_report(
            "2026-09-10",
            VALID_PARAMETERS,
            page_token=" ",
        )


def test_customer_usage_get_uses_one_page_without_retry(monkeypatch):
    request = httpx.Request(
        "GET",
        customer_usage.CUSTOMER_USAGE_REPORT_URL.format(
            date="2026-09-10",
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

    monkeypatch.setattr(customer_usage.httpx, "Client", FakeClient)
    monkeypatch.setattr(
        customer_usage,
        "get_workspace_access_token",
        lambda **kwargs: ("test-value", 3600),
    )

    with pytest.raises(httpx.HTTPStatusError) as caught:
        customer_usage.get_customer_usage_report("2026-09-10", VALID_PARAMETERS)

    assert caught.value.response is response
    assert calls == [
        (
            customer_usage.CUSTOMER_USAGE_REPORT_URL.format(
                date="2026-09-10",
            ),
            {"parameters": VALID_PARAMETERS},
        )
    ]


def test_customer_usage_serializer_is_allowlisted_and_sanitizes_response():
    page = {
        "usage_reports": [
            {
                "kind": "usageReport",
                "etag": "omit-etag",
                "date": "2026-09-10",
                "entity": {
                    "customerId": "omit-customer",
                    "userEmail": "omit@example.com",
                    "profileId": "omit-profile",
                    "entityId": "omit-entity",
                    "type": "customer",
                },
                "parameters": [
                    {"name": "accounts:num_users", "intValue": 10},
                    {
                        "name": "accounts:used_quota_in_mb",
                        "intValue": 20,
                    },
                    {
                        "name": "accounts:num_suspended_users",
                        "intValue": 30,
                    },
                    {
                        "name": "accounts:num_archived_users",
                        "stringValue": "omit",
                    },
                    {
                        "name": "accounts:num_disabled_accounts",
                        "datetimeValue": "omit",
                    },
                    {
                        "name": "accounts:customer_used_quota_in_mb",
                        "msgValue": {"parameter": []},
                    },
                    {
                        "name": "accounts:gmail_used_quota_in_mb",
                        "boolValue": True,
                    },
                    {"name": "accounts:unknown", "intValue": 99},
                ],
            }
        ],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 2,
    }

    result = server._serialize_customer_usage_page(
        page,
        parameters="accounts:num_users,accounts:used_quota_in_mb",
    )

    assert result == {
        "usage_reports": [
            {
                "date": "2026-09-10",
                "parameters": [
                    {
                        "parameter_name": "accounts:num_users",
                        "integer_value": 10,
                    },
                    {
                        "parameter_name": "accounts:used_quota_in_mb",
                        "integer_value": 20,
                    },
                ],
            }
        ],
        "next_page_token": "next-page",
        "warnings_present": True,
        "warnings_count": 2,
    }
    assert "customerId" not in str(result)
    assert "userEmail" not in str(result)
    assert "profileId" not in str(result)
    assert "entityId" not in str(result)
    assert "kind" not in str(result)
    assert "etag" not in str(result)
    assert "string_value" not in str(result)
    assert "datetime_value" not in str(result)
    assert "msgValue" not in str(result)
    assert "boolean_value" not in str(result)
    assert "raw" not in result


def test_customer_usage_serializer_omits_incompatible_integer_values():
    result = server._serialize_customer_usage_report(
        {
            "date": "2026-09-10",
            "parameters": [
                {"name": "accounts:num_users", "intValue": "10"},
                {"name": "accounts:num_users", "intValue": True},
                {"name": "accounts:num_users", "intValue": 10},
            ],
        },
        requested_parameters={"accounts:num_users"},
    )

    assert result["parameters"] == [
        {"parameter_name": "accounts:num_users", "integer_value": 10}
    ]
