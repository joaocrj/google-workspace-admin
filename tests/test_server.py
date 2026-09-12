import pytest

from google_workspace_admin import server


def test_workspace_status():
    result = server.workspace_status()

    assert result["status"] == "ok"
    assert result["server"] == "google-workspace-admin"
    assert result["authentication"] == "ADC -> IAM signJwt -> DWD"


def test_workspace_users_list(monkeypatch):
    fake_users = [
        {
            "id": "123",
            "primaryEmail": "teste@example.com",
            "name": {
                "fullName": "Usuário Teste",
                "givenName": "Usuário",
                "familyName": "Teste",
            },
            "suspended": False,
            "archived": False,
            "isAdmin": False,
            "isDelegatedAdmin": False,
            "orgUnitPath": "/Teste",
            "creationTime": "2026-01-01T00:00:00.000Z",
            "lastLoginTime": "2026-09-01T12:00:00.000Z",
        }
    ]

    monkeypatch.setattr(
        server,
        "list_users",
        lambda max_results=5: fake_users,
    )

    result = server.workspace_users_list(max_results=5)

    assert len(result) == 1
    assert result[0]["primary_email"] == "teste@example.com"
    assert result[0]["full_name"] == "Usuário Teste"
    assert result[0]["suspended"] is False
    assert result[0]["org_unit_path"] == "/Teste"


def test_workspace_user_get(monkeypatch):
    fake_user = {
        "id": "456",
        "primaryEmail": "adm@example.com",
        "name": {
            "fullName": "Administrador",
            "givenName": "Administrador",
            "familyName": "",
        },
        "suspended": False,
        "archived": False,
        "isAdmin": True,
        "isDelegatedAdmin": False,
        "orgUnitPath": "/",
        "creationTime": "2026-01-01T00:00:00.000Z",
        "lastLoginTime": "2026-09-03T12:00:00.000Z",
    }

    monkeypatch.setattr(
        server,
        "get_user",
        lambda user_key: fake_user,
    )

    result = server.workspace_user_get(
        "adm@example.com"
    )

    assert result["id"] == "456"
    assert result["primary_email"] == "adm@example.com"
    assert result["full_name"] == "Administrador"
    assert result["is_admin"] is True


def test_workspace_users_list_rejects_zero():
    try:
        server.workspace_users_list(max_results=0)
    except ValueError as exc:
        assert "entre 1 e 100" in str(exc)
    else:
        raise AssertionError("ValueError esperado.")


def test_workspace_users_list_rejects_above_100():
    try:
        server.workspace_users_list(max_results=101)
    except ValueError as exc:
        assert "entre 1 e 100" in str(exc)
    else:
        raise AssertionError("ValueError esperado.")
        
def test_workspace_groups_list(monkeypatch):
    fake_groups = [
        {
            "id": "group-123",
            "email": "classroom_teachers@cevalente.com.br",
            "name": "Classroom Teachers",
            "description": "Grupo de professores",
            "directMembersCount": "3",
            "adminCreated": True,
        }
    ]

    monkeypatch.setattr(
        "google_workspace_admin.server.list_groups",
        lambda max_results: fake_groups,
    )

    result = server.workspace_groups_list(max_results=10)

    assert result == [
        {
            "id": "group-123",
            "email": "classroom_teachers@cevalente.com.br",
            "name": "Classroom Teachers",
            "description": "Grupo de professores",
            "direct_members_count": "3",
            "admin_created": True,
        }
    ]

def test_workspace_groups_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_groups_list(max_results=0)


def test_workspace_groups_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_groups_list(max_results=201)

def test_workspace_group_members_list(monkeypatch):
    fake_members = [
        {
            "id": "member-123",
            "email": "usuario@cevalente.com.br",
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "delivery_settings": "ALL_MAIL",
        }
    ]

    monkeypatch.setattr(
        "google_workspace_admin.server.list_group_members",
        lambda group_key, max_results: fake_members,
    )

    result = server.workspace_group_members_list(
        group_key="grupo@cevalente.com.br",
        max_results=100,
    )

    assert result == [
        {
            "id": "member-123",
            "email": "usuario@cevalente.com.br",
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "delivery_settings": "ALL_MAIL",
        }
    ]


def test_workspace_group_members_list_rejects_empty_group_key():
    with pytest.raises(
        ValueError,
        match="group_key não pode estar vazio",
    ):
        server.workspace_group_members_list(
            group_key="   ",
            max_results=100,
        )


def test_workspace_group_members_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_group_members_list(
            group_key="grupo@cevalente.com.br",
            max_results=0,
        )


def test_workspace_group_members_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 200",
    ):
        server.workspace_group_members_list(
            group_key="grupo@cevalente.com.br",
            max_results=201,
        )

def test_workspace_orgunits_list(monkeypatch):
    fake_orgunits = [
        {
            "orgUnitId": "id:cev-users",
            "name": "CEV_USERS",
            "description": "Usuários da organização",
            "orgUnitPath": "/CEV_USERS",
            "parentOrgUnitId": "id:root",
            "parentOrgUnitPath": "/",
            "blockInheritance": False,
        }
    ]

    monkeypatch.setattr(
        "google_workspace_admin.server.list_orgunits",
        lambda org_unit_path, org_unit_type: fake_orgunits,
    )

    result = server.workspace_orgunits_list(
        org_unit_path="/CEV_USERS",
        org_unit_type="all_including_parent",
    )

    assert result == [
        {
            "org_unit_id": "id:cev-users",
            "name": "CEV_USERS",
            "description": "Usuários da organização",
            "org_unit_path": "/CEV_USERS",
            "parent_org_unit_id": "id:root",
            "parent_org_unit_path": "/",
            "block_inheritance": False,
        }
    ]


def test_workspace_orgunits_list_uses_defaults(monkeypatch):
    captured = {}

    def fake_list_orgunits(
        org_unit_path="/",
        org_unit_type="all",
    ):
        captured["org_unit_path"] = org_unit_path
        captured["org_unit_type"] = org_unit_type
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_orgunits",
        fake_list_orgunits,
    )

    result = server.workspace_orgunits_list()

    assert result == []
    assert captured["org_unit_path"] == "/"
    assert captured["org_unit_type"] == "all"


def test_workspace_orgunits_list_accepts_children(monkeypatch):
    captured = {}

    def fake_list_orgunits(
        org_unit_path,
        org_unit_type,
    ):
        captured["org_unit_path"] = org_unit_path
        captured["org_unit_type"] = org_unit_type
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_orgunits",
        fake_list_orgunits,
    )

    result = server.workspace_orgunits_list(
        org_unit_path="/CEV_USERS",
        org_unit_type="children",
    )

    assert result == []
    assert captured["org_unit_path"] == "/CEV_USERS"
    assert captured["org_unit_type"] == "children"


def test_workspace_orgunits_list_rejects_empty_path():
    with pytest.raises(
        ValueError,
        match="org_unit_path não pode estar vazio",
    ):
        server.workspace_orgunits_list(
            org_unit_path="   ",
        )


def test_workspace_orgunits_list_rejects_path_without_slash():
    with pytest.raises(
        ValueError,
        match="org_unit_path deve começar com '/'",
    ):
        server.workspace_orgunits_list(
            org_unit_path="CEV_USERS",
        )


def test_workspace_orgunits_list_rejects_invalid_type():
    with pytest.raises(
        ValueError,
        match="org_unit_type deve ser",
    ):
        server.workspace_orgunits_list(
            org_unit_path="/",
            org_unit_type="invalid",
        )

def test_workspace_mobile_devices_list(monkeypatch):
    fake_devices = [
        {
            "resourceId": "resource-123",
            "deviceId": "device-123",
            "name": ["Usuário Teste"],
            "email": ["teste@cevalente.com.br"],
            "model": "SM-A155M",
            "manufacturer": "Samsung",
            "type": "ANDROID",
            "os": "Android 16",
            "status": "APPROVED",
            "firstSync": "2026-01-01T10:00:00.000Z",
            "lastSync": "2026-09-08T12:00:00.000Z",
            "hardwareId": "hardware-123",
            "serialNumber": "serial-123",
            "imei": "imei-123",
            "meid": "meid-123",
            "wifiMacAddress": "00:11:22:33:44:55",
            "networkOperator": "Claro",
            "defaultLanguage": "pt-BR",
            "managedAccountIsOnOwnerProfile": True,
        }
    ]

    monkeypatch.setattr(
        "google_workspace_admin.server.list_mobile_devices",
        lambda max_results=100: fake_devices,
    )

    result = server.workspace_mobile_devices_list(
        max_results=50,
    )

    assert result == [
        {
            "resource_id": "resource-123",
            "device_id": "device-123",
            "name": ["Usuário Teste"],
            "email": ["teste@cevalente.com.br"],
            "model": "SM-A155M",
            "manufacturer": "Samsung",
            "type": "ANDROID",
            "os": "Android 16",
            "status": "APPROVED",
            "first_sync": "2026-01-01T10:00:00.000Z",
            "last_sync": "2026-09-08T12:00:00.000Z",
            "hardware_id": "hardware-123",
            "serial_number": "serial-123",
            "imei": "imei-123",
            "meid": "meid-123",
            "wifi_mac_address": "00:11:22:33:44:55",
            "network_operator": "Claro",
            "default_language": "pt-BR",
            "managed_account_is_on_owner_profile": True,
        }
    ]


def test_workspace_mobile_devices_list_uses_default(monkeypatch):
    captured = {}

    def fake_list_mobile_devices(max_results=100):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_mobile_devices",
        fake_list_mobile_devices,
    )

    result = server.workspace_mobile_devices_list()

    assert result == []
    assert captured["max_results"] == 100


def test_workspace_mobile_devices_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_mobile_devices_list(
            max_results=0,
        )


def test_workspace_mobile_devices_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_mobile_devices_list(
            max_results=101,
        )

def test_workspace_chromeos_devices_list(monkeypatch):
    fake_devices = [
        {
            "deviceId": "chromeos-device-123",
            "serialNumber": "SERIAL-123",
            "model": "Chromebook Plus",
            "manufacturer": "Acer",
            "status": "ACTIVE",
            "osVersion": "140.0.7339.185",
            "platformVersion": "16371.68.0",
            "firmwareVersion": "Google_Test.12345",
            "macAddress": "00:11:22:33:44:55",
            "ethernetMacAddress": "00:11:22:33:44:66",
            "orgUnitPath": "/CEV_USERS",
            "annotatedUser": "usuario@cevalente.com.br",
            "annotatedLocation": "Escritório",
            "annotatedAssetId": "ASSET-123",
            "lastSync": "2026-09-10T12:00:00.000Z",
            "lastEnrollmentTime": "2026-01-01T10:00:00.000Z",
            "supportEndDate": "2030-01-01T00:00:00.000Z",
            "notes": "Equipamento de teste",
        }
    ]

    monkeypatch.setattr(
        "google_workspace_admin.server.list_chromeos_devices",
        lambda max_results=100: fake_devices,
    )

    result = server.workspace_chromeos_devices_list(
        max_results=50,
    )

    assert result == [
        {
            "device_id": "chromeos-device-123",
            "serial_number": "SERIAL-123",
            "model": "Chromebook Plus",
            "manufacturer": "Acer",
            "status": "ACTIVE",
            "os_version": "140.0.7339.185",
            "platform_version": "16371.68.0",
            "firmware_version": "Google_Test.12345",
            "mac_address": "00:11:22:33:44:55",
            "ethernet_mac_address": "00:11:22:33:44:66",
            "org_unit_path": "/CEV_USERS",
            "annotated_user": "usuario@cevalente.com.br",
            "annotated_location": "Escritório",
            "annotated_asset_id": "ASSET-123",
            "last_sync": "2026-09-10T12:00:00.000Z",
            "last_enrollment_time": "2026-01-01T10:00:00.000Z",
            "support_end_date": "2030-01-01T00:00:00.000Z",
            "notes": "Equipamento de teste",
        }
    ]


def test_workspace_chromeos_devices_list_uses_default(monkeypatch):
    captured = {}

    def fake_list_chromeos_devices(max_results=100):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(
        "google_workspace_admin.server.list_chromeos_devices",
        fake_list_chromeos_devices,
    )

    result = server.workspace_chromeos_devices_list()

    assert result == []
    assert captured["max_results"] == 100


def test_workspace_chromeos_devices_list_rejects_zero():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 300",
    ):
        server.workspace_chromeos_devices_list(
            max_results=0,
        )


def test_workspace_chromeos_devices_list_rejects_above_limit():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 300",
    ):
        server.workspace_chromeos_devices_list(
            max_results=301,
        )
def test_workspace_roles_list(monkeypatch):
    fake_roles = [
        {
            "roleId": "role-123",
            "roleName": "_SEED_ADMIN_ROLE",
            "roleDescription": "Super administrador",
            "rolePrivileges": [
                {
                    "privilegeName": "USERS_RETRIEVE",
                    "serviceId": "00haapch16h1ysv",
                }
            ],
            "isSystemRole": True,
            "isSuperAdminRole": True,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_roles",
        lambda max_results=100: fake_roles,
    )

    result = server.workspace_roles_list(
        max_results=50,
    )

    assert result == [
        {
            "role_id": "role-123",
            "role_name": "_SEED_ADMIN_ROLE",
            "role_description": "Super administrador",
            "role_privileges": [
                {
                    "privilegeName": "USERS_RETRIEVE",
                    "serviceId": "00haapch16h1ysv",
                }
            ],
            "is_system_role": True,
            "is_super_admin_role": True,
        }
    ]


def test_workspace_roles_list_uses_default(monkeypatch):
    captured = {}

    def fake_list_roles(max_results=100):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(
        server,
        "list_roles",
        fake_list_roles,
    )

    result = server.workspace_roles_list()

    assert result == []
    assert captured["max_results"] == 100


def test_workspace_roles_list_rejects_invalid_limits():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_roles_list(max_results=0)

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_roles_list(max_results=101)


def test_workspace_role_assignments_list(monkeypatch):
    fake_assignments = [
        {
            "roleAssignmentId": "assignment-123",
            "roleId": "role-123",
            "assignedTo": "100056319502616315227",
            "scopeType": "CUSTOMER",
            "orgUnitId": None,
        }
    ]

    monkeypatch.setattr(
        server,
        "list_role_assignments",
        lambda max_results=100: fake_assignments,
    )

    result = server.workspace_role_assignments_list(
        max_results=50,
    )

    assert result == [
        {
            "role_assignment_id": "assignment-123",
            "role_id": "role-123",
            "assigned_to": "100056319502616315227",
            "scope_type": "CUSTOMER",
            "org_unit_id": None,
        }
    ]


def test_workspace_role_assignments_list_uses_default(monkeypatch):
    captured = {}

    def fake_list_role_assignments(max_results=100):
        captured["max_results"] = max_results
        return []

    monkeypatch.setattr(
        server,
        "list_role_assignments",
        fake_list_role_assignments,
    )

    result = server.workspace_role_assignments_list()

    assert result == []
    assert captured["max_results"] == 100


def test_workspace_role_assignments_list_rejects_invalid_limits():
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_role_assignments_list(max_results=0)

    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 100",
    ):
        server.workspace_role_assignments_list(max_results=101)

def test_workspace_domains_list(monkeypatch):
    fake_domains = [
        {
            "domainName": "cevalente.com.br",
            "verified": True,
            "isPrimary": True,
            "creationTime": "1586464166558",
            "domainAliases": [
                {
                    "kind": "admin#directory#domainAlias",
                    "etag": "alias-etag",
                    "domainAliasName": "cevalente.com.br.test-google-a.com",
                    "parentDomainName": "cevalente.com.br",
                    "verified": True,
                    "creationTime": "1586464166558",
                }
            ],
        }
    ]

    monkeypatch.setattr(
        server,
        "list_domains",
        lambda: fake_domains,
    )

    result = server.workspace_domains_list()

    assert result == [
        {
            "domain_name": "cevalente.com.br",
            "verified": True,
            "is_primary": True,
            "creation_time": "1586464166558",
            "domain_aliases": [
                {
                    "kind": "admin#directory#domainAlias",
                    "etag": "alias-etag",
                    "domainAliasName": "cevalente.com.br.test-google-a.com",
                    "parentDomainName": "cevalente.com.br",
                    "verified": True,
                    "creationTime": "1586464166558",
                }
            ],
        }
    ]

def test_workspace_domain_aliases_list(monkeypatch):
    domain_aliases = [
        {
            "domainAliasName": "cevalente.com.br.test-google-a.com",
            "parentDomainName": "cevalente.com.br",
            "verified": True,
            "creationTime": "1586464166558",
        }
    ]

    captured = {}

    def fake_list_domain_aliases(parent_domain_name=None):
        captured["parent_domain_name"] = parent_domain_name
        return domain_aliases

    monkeypatch.setattr(
        server,
        "list_domain_aliases",
        fake_list_domain_aliases,
    )

    result = server.workspace_domain_aliases_list(
        parent_domain_name="cevalente.com.br"
    )

    assert captured["parent_domain_name"] == "cevalente.com.br"
    assert result == [
        {
            "domain_alias_name": "cevalente.com.br.test-google-a.com",
            "parent_domain_name": "cevalente.com.br",
            "verified": True,
            "creation_time": "1586464166558",
        }
    ]


def test_workspace_buildings_list_serializes_a_page(monkeypatch):
    captured = {}

    def fake_list_buildings(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {
            "buildings": [
                {
                    "buildingId": "test-building",
                    "buildingName": "Test Building",
                    "description": "Test description",
                    "floorNames": ["floor-1", "floor-2", "floor-3"],
                    "coordinates": {
                        "latitude": 1.0,
                        "longitude": 2.0,
                    },
                    "address": {
                        "regionCode": "XX",
                        "languageCode": "test",
                        "postalCode": "00000",
                        "administrativeArea": "Test Area",
                        "locality": "Test Locality",
                        "sublocality": "Test Sublocality",
                        "addressLines": ["Test Address"],
                    },
                    "kind": "admin#directory#resources#buildings",
                    "etags": "test-etag",
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(server, "list_buildings", fake_list_buildings)

    result = server.workspace_buildings_list(
        max_results=500,
        page_token="test-page",
    )

    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
    }
    assert result == {
        "buildings": [
            {
                "building_id": "test-building",
                "building_name": "Test Building",
                "description": "Test description",
                "floor_names": ["floor-1", "floor-2", "floor-3"],
                "coordinates": {
                    "latitude": 1.0,
                    "longitude": 2.0,
                },
                "address": {
                    "region_code": "XX",
                    "language_code": "test",
                    "postal_code": "00000",
                    "administrative_area": "Test Area",
                    "locality": "Test Locality",
                    "sublocality": "Test Sublocality",
                    "address_lines": ["Test Address"],
                },
            }
        ],
        "next_page_token": "test-page",
    }
    assert "kind" not in result["buildings"][0]
    assert "etags" not in result["buildings"][0]


def test_workspace_buildings_list_uses_default_page_arguments(monkeypatch):
    captured = {}

    def fake_list_buildings(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {"buildings": [], "next_page_token": None}

    monkeypatch.setattr(server, "list_buildings", fake_list_buildings)

    assert server.workspace_buildings_list() == {
        "buildings": [],
        "next_page_token": None,
    }
    assert captured == {"max_results": 100, "page_token": None}


@pytest.mark.parametrize("max_results", [0, 501])
def test_workspace_buildings_list_rejects_invalid_page_limits(max_results):
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        server.workspace_buildings_list(max_results=max_results)


@pytest.mark.parametrize("page_token", ["", "  ", "\t"])
def test_workspace_buildings_list_rejects_blank_page_tokens(page_token):
    with pytest.raises(
        ValueError,
        match="page_token não pode estar vazio",
    ):
        server.workspace_buildings_list(page_token=page_token)


def test_workspace_calendar_resources_list_serializes_a_page(monkeypatch):
    captured = {}

    def fake_list_calendar_resources(
        max_results=100,
        page_token=None,
        order_by=None,
        query=None,
    ):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        captured["order_by"] = order_by
        captured["query"] = query
        return {
            "resources": [
                {
                    "resourceId": "test-resource",
                    "resourceName": "Test Resource",
                    "resourceDescription": "Test description",
                    "resourceType": "CONFERENCE_ROOM",
                    "resourceEmail": "resource@example.com",
                    "resourceCategory": "CONFERENCE_ROOM",
                    "userVisibleDescription": "Test visible description",
                    "generatedResourceName": "test-resource",
                    "capacity": 10,
                    "buildingId": "test-building",
                    "floorName": "floor-1",
                    "floorSection": "section-1",
                    "kind": "admin#directory#resources#calendars#CalendarResource",
                    "etags": "test-etag",
                    "featureInstances": [{"feature": {"name": "display"}}],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_calendar_resources",
        fake_list_calendar_resources,
    )

    result = server.workspace_calendar_resources_list(
        max_results=500,
        page_token="test-page",
        order_by="capacity desc",
        query="resourceCategory=CONFERENCE_ROOM",
    )

    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
        "order_by": "capacity desc",
        "query": "resourceCategory=CONFERENCE_ROOM",
    }
    assert result == {
        "resources": [
            {
                "resource_id": "test-resource",
                "resource_name": "Test Resource",
                "resource_description": "Test description",
                "resource_type": "CONFERENCE_ROOM",
                "resource_email": "resource@example.com",
                "resource_category": "CONFERENCE_ROOM",
                "user_visible_description": "Test visible description",
                "generated_resource_name": "test-resource",
                "capacity": 10,
                "building_id": "test-building",
                "floor_name": "floor-1",
                "floor_section": "section-1",
            }
        ],
        "next_page_token": "test-page",
    }
    assert "kind" not in result["resources"][0]
    assert "etags" not in result["resources"][0]
    assert "feature_instances" not in result["resources"][0]


def test_workspace_calendar_resources_list_uses_default_page_arguments(
    monkeypatch,
):
    captured = {}

    def fake_list_calendar_resources(
        max_results=100,
        page_token=None,
        order_by=None,
        query=None,
    ):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        captured["order_by"] = order_by
        captured["query"] = query
        return {"resources": [], "next_page_token": None}

    monkeypatch.setattr(
        server,
        "list_calendar_resources",
        fake_list_calendar_resources,
    )

    assert server.workspace_calendar_resources_list() == {
        "resources": [],
        "next_page_token": None,
    }
    assert captured == {
        "max_results": 100,
        "page_token": None,
        "order_by": None,
        "query": None,
    }


@pytest.mark.parametrize("max_results", [0, 501])
def test_workspace_calendar_resources_list_rejects_invalid_page_limits(
    max_results,
):
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        server.workspace_calendar_resources_list(max_results=max_results)


@pytest.mark.parametrize(
    ("parameter_name", "value"),
    [
        ("page_token", ""),
        ("page_token", "  "),
        ("order_by", "\t"),
        ("query", "   "),
    ],
)
def test_workspace_calendar_resources_list_rejects_blank_strings(
    parameter_name,
    value,
):
    with pytest.raises(
        ValueError,
        match=f"{parameter_name} não pode estar vazio",
    ):
        server.workspace_calendar_resources_list(**{parameter_name: value})


def test_workspace_calendar_features_list_serializes_a_page(monkeypatch):
    captured = {}

    def fake_list_calendar_features(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {
            "features": [
                {
                    "name": "test-feature",
                    "kind": "admin#directory#resources#features#Feature",
                    "etags": "test-etag",
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_calendar_features",
        fake_list_calendar_features,
    )

    result = server.workspace_calendar_features_list(
        max_results=500,
        page_token="test-page",
    )

    assert captured == {
        "max_results": 500,
        "page_token": "test-page",
    }
    assert result == {
        "features": [{"feature_name": "test-feature"}],
        "next_page_token": "test-page",
    }
    assert "kind" not in result["features"][0]
    assert "etags" not in result["features"][0]


def test_workspace_calendar_features_list_uses_default_page_arguments(
    monkeypatch,
):
    captured = {}

    def fake_list_calendar_features(max_results=100, page_token=None):
        captured["max_results"] = max_results
        captured["page_token"] = page_token
        return {"features": [], "next_page_token": None}

    monkeypatch.setattr(
        server,
        "list_calendar_features",
        fake_list_calendar_features,
    )

    assert server.workspace_calendar_features_list() == {
        "features": [],
        "next_page_token": None,
    }
    assert captured == {"max_results": 100, "page_token": None}


@pytest.mark.parametrize("max_results", [0, 501])
def test_workspace_calendar_features_list_rejects_invalid_page_limits(
    max_results,
):
    with pytest.raises(
        ValueError,
        match="max_results deve estar entre 1 e 500",
    ):
        server.workspace_calendar_features_list(max_results=max_results)


@pytest.mark.parametrize("page_token", ["", "  ", "\t"])
def test_workspace_calendar_features_list_rejects_blank_page_tokens(
    page_token,
):
    with pytest.raises(
        ValueError,
        match="page_token não pode estar vazio",
    ):
        server.workspace_calendar_features_list(page_token=page_token)


def test_workspace_admin_audit_list_serializes_a_page(monkeypatch):
    captured = {}

    def fake_list_admin_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "kind": "audit#activity",
                    "etag": "test-etag",
                    "ownerDomain": "example.com",
                    "ipAddress": "198.51.100.10",
                    "id": {
                        "time": "0",
                        "uniqueQualifier": "1",
                        "applicationName": "admin",
                        "customerId": "customer-id",
                    },
                    "actor": {
                        "email": "admin@example.com",
                        "callerType": "USER",
                        "profileId": "profile-id",
                        "key": "actor-key",
                        "applicationInfo": {
                            "oauthClientId": "client-id",
                        },
                    },
                    "networkInfo": {"regionCode": "BR"},
                    "resourceDetails": [{"id": "resource-id"}],
                    "events": [
                        {
                            "type": "SETTINGS",
                            "name": "CHANGE_SETTING",
                            "parameters": [
                                {"name": "string", "value": "value"},
                                {
                                    "name": "multi-string",
                                    "multiValue": [],
                                },
                                {"name": "integer", "intValue": "0"},
                                {
                                    "name": "multi-integer",
                                    "multiIntValue": ["0", "1"],
                                },
                                {"name": "boolean-true", "boolValue": True},
                                {"name": "boolean-false", "boolValue": False},
                                {
                                    "name": "nested",
                                    "messageValue": {
                                        "parameter": [
                                            {
                                                "name": "nested-false",
                                                "boolValue": False,
                                            }
                                        ]
                                    },
                                },
                                {
                                    "name": "nested-sets",
                                    "multiMessageValue": [
                                        {
                                            "parameter": [
                                                {
                                                    "name": "first",
                                                    "value": "one",
                                                }
                                            ]
                                        },
                                        {
                                            "parameter": [
                                                {
                                                    "name": "second",
                                                    "intValue": "0",
                                                }
                                            ]
                                        },
                                    ],
                                },
                            ],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                            "resourceIds": ["resource-id"],
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_admin_audit_activities",
        fake_list_admin_audit_activities,
    )

    result = server.workspace_admin_audit_list(
        max_results=100,
        page_token="test-page",
        user_key="admin@example.com",
        event_name="CHANGE_SETTING",
        filters="SETTING_NAME==EXAMPLE",
        start_time="2026-09-10T00:00:00Z",
        end_time="2026-09-11T00:00:00Z",
        actor_ip_address="198.51.100.10",
        org_unit_id="id:org-unit",
    )

    assert captured == {
        "max_results": 100,
        "page_token": "test-page",
        "user_key": "admin@example.com",
        "event_name": "CHANGE_SETTING",
        "filters": "SETTING_NAME==EXAMPLE",
        "start_time": "2026-09-10T00:00:00Z",
        "end_time": "2026-09-11T00:00:00Z",
        "actor_ip_address": "198.51.100.10",
        "org_unit_id": "id:org-unit",
    }
    assert result == {
        "activities": [
            {
                "occurred_at_epoch_seconds": "0",
                "activity_qualifier": "1",
                "actor": {
                    "email": "admin@example.com",
                    "caller_type": "USER",
                },
                "actor_ip_address": "198.51.100.10",
                "events": [
                    {
                        "event_type": "SETTINGS",
                        "event_name": "CHANGE_SETTING",
                        "parameters": [
                            {
                                "parameter_name": "string",
                                "string_value": "value",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "multi-string",
                                "string_value": None,
                                "string_values": [],
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "integer",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": "0",
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "multi-integer",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": ["0", "1"],
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "boolean-true",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": True,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "boolean-false",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": False,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "nested",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": [
                                    {
                                        "parameter_name": "nested-false",
                                        "string_value": None,
                                        "string_values": None,
                                        "integer_value": None,
                                        "integer_values": None,
                                        "boolean_value": False,
                                    }
                                ],
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "nested-sets",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": [
                                    [
                                        {
                                            "parameter_name": "first",
                                            "string_value": "one",
                                            "string_values": None,
                                            "integer_value": None,
                                            "integer_values": None,
                                            "boolean_value": None,
                                        }
                                    ],
                                    [
                                        {
                                            "parameter_name": "second",
                                            "string_value": None,
                                            "string_values": None,
                                            "integer_value": "0",
                                            "integer_values": None,
                                            "boolean_value": None,
                                        }
                                    ],
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
        "next_page_token": "test-page",
    }

    serialized_activity = result["activities"][0]
    assert "kind" not in serialized_activity
    assert "etag" not in serialized_activity
    assert "ownerDomain" not in serialized_activity
    assert "profileId" not in serialized_activity["actor"]
    assert "key" not in serialized_activity["actor"]
    assert "networkInfo" not in serialized_activity
    assert "resourceDetails" not in serialized_activity
    serialized_event = serialized_activity["events"][0]
    assert "sensitiveParameters" not in serialized_event
    assert "resourceIds" not in serialized_event


def test_workspace_admin_audit_list_uses_safe_default_arguments(monkeypatch):
    captured = {}

    def fake_list_admin_audit_activities(**kwargs):
        captured.update(kwargs)
        return {"activities": [], "next_page_token": None}

    monkeypatch.setattr(
        server,
        "list_admin_audit_activities",
        fake_list_admin_audit_activities,
    )

    assert server.workspace_admin_audit_list() == {
        "activities": [],
        "next_page_token": None,
    }
    assert captured == {
        "max_results": 25,
        "page_token": None,
        "user_key": "all",
        "event_name": None,
        "filters": None,
        "start_time": None,
        "end_time": None,
        "actor_ip_address": None,
        "org_unit_id": None,
    }


def test_admin_audit_serializers_handle_absent_fields():
    assert server._serialize_admin_audit_nested_parameter({}) == {
        "parameter_name": None,
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": None,
    }
    assert server._serialize_admin_audit_parameter({}) == {
        "parameter_name": None,
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": None,
        "nested_parameters": None,
        "nested_parameter_sets": None,
    }
    assert server._serialize_admin_audit_event({}) == {
        "event_type": None,
        "event_name": None,
        "parameters": [],
    }
    assert server._serialize_admin_audit_activity({}) == {
        "occurred_at_epoch_seconds": None,
        "activity_qualifier": None,
        "actor": {
            "email": None,
            "caller_type": None,
        },
        "actor_ip_address": None,
        "events": [],
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "  "},
        {"user_key": "\t"},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
def test_workspace_admin_audit_list_rejects_invalid_arguments(arguments):
    with pytest.raises(ValueError):
        server.workspace_admin_audit_list(**arguments)


def test_workspace_login_audit_list_serializes_conservatively(monkeypatch):
    captured = {}

    def fake_list_login_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "kind": "audit#activity",
                    "etag": "omit-etag",
                    "ownerDomain": "omit.example",
                    "ipAddress": "198.51.100.20",
                    "id": {
                        "time": "123",
                        "uniqueQualifier": "456",
                        "applicationName": "login",
                        "customerId": "omit-customer",
                    },
                    "actor": {
                        "email": "actor@example.com",
                        "callerType": "USER",
                        "profileId": "omit-profile",
                        "key": "omit-key",
                        "applicationInfo": {
                            "oauthClientId": "omit-client",
                        },
                    },
                    "networkInfo": {"regionCode": "BR"},
                    "resourceDetails": [{"id": "omit-resource"}],
                    "userDeviceInfo": {"deviceId": "omit-device"},
                    "events": [
                        {
                            "type": "login",
                            "name": "login_success",
                            "status": {"statusCode": "200"},
                            "resourceIds": ["omit-resource-id"],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                            "parameters": [
                                {
                                    "name": "login_type",
                                    "value": "google_password",
                                },
                                {
                                    "name": "login_challenge_method",
                                    "multiValue": [],
                                },
                                {
                                    "name": "login_challenge_status",
                                    "value": "Challenge Passed.",
                                },
                                {
                                    "name": "is_suspicious",
                                    "boolValue": False,
                                },
                                {
                                    "name": "is_second_factor",
                                    "boolValue": True,
                                },
                                {
                                    "name": "affected_email_address",
                                    "value": "omit-user@example.com",
                                },
                                {
                                    "name": "login_timestamp",
                                    "intValue": "0",
                                },
                                {
                                    "name": "sensitive_action_name",
                                    "value": "omit-action",
                                },
                                {
                                    "name": "login_failure_type",
                                    "value": "omit-failure",
                                },
                                {
                                    "name": "unknown_parameter",
                                    "value": "omit-unknown",
                                    "intValue": "0",
                                },
                                {
                                    "name": "nested",
                                    "messageValue": {
                                        "parameter": [
                                            {
                                                "name": "nested-secret",
                                                "value": "omit-nested",
                                            }
                                        ]
                                    },
                                },
                            ],
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_login_audit_activities",
        fake_list_login_audit_activities,
    )

    result = server.workspace_login_audit_list(
        max_results=1,
        page_token="test-page",
        user_key="user@example.com",
        event_name="login_success",
        filters="is_suspicious==false",
        start_time="2026-09-10T00:00:00Z",
        end_time="2026-09-11T00:00:00Z",
        actor_ip_address="198.51.100.20",
        org_unit_id="id:org-unit",
    )

    assert captured == {
        "max_results": 1,
        "page_token": "test-page",
        "user_key": "user@example.com",
        "event_name": "login_success",
        "filters": "is_suspicious==false",
        "start_time": "2026-09-10T00:00:00Z",
        "end_time": "2026-09-11T00:00:00Z",
        "actor_ip_address": "198.51.100.20",
        "org_unit_id": "id:org-unit",
    }
    assert result == {
        "activities": [
            {
                "occurred_at_epoch_seconds": "123",
                "activity_qualifier": "456",
                "actor": {
                    "email": "actor@example.com",
                    "caller_type": "USER",
                },
                "actor_ip_address": "198.51.100.20",
                "events": [
                    {
                        "event_type": "login",
                        "event_name": "login_success",
                        "parameters": [
                            {
                                "parameter_name": "login_type",
                                "string_value": "google_password",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "login_challenge_method",
                                "string_value": None,
                                "string_values": [],
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "login_challenge_status",
                                "string_value": "Challenge Passed.",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "is_suspicious",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": False,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "is_second_factor",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": True,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "affected_email_address",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "login_timestamp",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "sensitive_action_name",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "login_failure_type",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "unknown_parameter",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "nested",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": [
                                    {"parameter_name": "nested-secret"}
                                ],
                                "nested_parameter_sets": None,
                            },
                        ],
                    }
                ],
            }
        ],
        "next_page_token": "test-page",
    }

    serialized_activity = result["activities"][0]
    assert "kind" not in serialized_activity
    assert "etag" not in serialized_activity
    assert "ownerDomain" not in serialized_activity
    assert "profileId" not in serialized_activity["actor"]
    assert "key" not in serialized_activity["actor"]
    assert "networkInfo" not in serialized_activity
    assert "resourceDetails" not in serialized_activity
    assert "userDeviceInfo" not in serialized_activity
    serialized_event = serialized_activity["events"][0]
    assert "sensitiveParameters" not in serialized_event
    assert "resourceIds" not in serialized_event
    assert "status" not in serialized_event
    assert "omit-user@example.com" not in str(result)
    assert "omit-action" not in str(result)
    assert "omit-nested" not in str(result)


def test_workspace_login_audit_list_uses_safe_default_arguments(monkeypatch):
    captured = {}

    def fake_list_login_audit_activities(**kwargs):
        captured.update(kwargs)
        return {"activities": [], "next_page_token": None}

    monkeypatch.setattr(
        server,
        "list_login_audit_activities",
        fake_list_login_audit_activities,
    )

    assert server.workspace_login_audit_list() == {
        "activities": [],
        "next_page_token": None,
    }
    assert captured == {
        "max_results": 25,
        "page_token": None,
        "user_key": "all",
        "event_name": None,
        "filters": None,
        "start_time": None,
        "end_time": None,
        "actor_ip_address": None,
        "org_unit_id": None,
    }


def test_login_audit_serializers_handle_absent_fields():
    assert server._serialize_login_audit_nested_parameter({}) == {
        "parameter_name": None,
    }
    assert server._serialize_login_audit_parameter({}) == {
        "parameter_name": None,
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": None,
        "nested_parameters": None,
        "nested_parameter_sets": None,
    }
    assert server._serialize_login_audit_event({}) == {
        "event_type": None,
        "event_name": None,
        "parameters": [],
    }
    assert server._serialize_login_audit_activity({}) == {
        "occurred_at_epoch_seconds": None,
        "activity_qualifier": None,
        "actor": {
            "email": None,
            "caller_type": None,
        },
        "actor_ip_address": None,
        "events": [],
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "  "},
        {"user_key": "\t"},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
def test_workspace_login_audit_list_rejects_invalid_arguments(
    monkeypatch,
    arguments,
):
    monkeypatch.setattr(
        server,
        "list_login_audit_activities",
        lambda **kwargs: pytest.fail("A chamada não deveria ocorrer."),
    )

    with pytest.raises(ValueError):
        server.workspace_login_audit_list(**arguments)


def test_workspace_drive_audit_list_serializes_with_drive_allowlist(monkeypatch):
    captured = {}

    def fake_list_drive_audit_activities(**kwargs):
        captured.update(kwargs)
        return {
            "activities": [
                {
                    "kind": "audit#activity",
                    "etag": "omit-etag",
                    "ownerDomain": "omit-domain",
                    "ipAddress": "198.51.100.12",
                    "networkInfo": {"regionCode": "BR"},
                    "resourceDetails": [{"id": "omit-resource"}],
                    "userDeviceInfo": {"deviceId": "omit-device"},
                    "isAgenticAction": True,
                    "id": {
                        "time": "123",
                        "uniqueQualifier": "456",
                        "applicationName": "drive",
                        "customerId": "omit-customer",
                    },
                    "actor": {
                        "email": "actor@example.com",
                        "callerType": "USER",
                        "profileId": "omit-profile",
                        "key": "omit-key",
                        "applicationInfo": {
                            "oauthClientId": "omit-client",
                        },
                    },
                    "events": [
                        {
                            "type": "DRIVE",
                            "name": "change_user_access",
                            "primaryEvent": False,
                            "parameters": [
                                {"name": "doc_id", "value": "doc-123"},
                                {
                                    "name": "shared_drive_id",
                                    "value": "drive-123",
                                },
                                {
                                    "name": "owner_shared_drive_id",
                                    "value": "owner-drive-123",
                                },
                                {"name": "doc_type", "value": "document"},
                                {
                                    "name": "visibility",
                                    "multiValue": [],
                                },
                                {"name": "billable", "boolValue": False},
                                {"name": "is_encrypted", "boolValue": True},
                                {
                                    "name": "owner_is_shared_drive",
                                    "boolValue": False,
                                },
                                {
                                    "name": "doc_title",
                                    "value": "omit title",
                                },
                                {
                                    "name": "target_user",
                                    "value": "omit-target@example.com",
                                },
                                {
                                    "name": "unknown_parameter",
                                    "value": "omit unknown",
                                },
                                {
                                    "name": "nested",
                                    "messageValue": {
                                        "parameter": [
                                            {
                                                "name": "doc_title",
                                                "value": "omit nested title",
                                            }
                                        ]
                                    },
                                },
                                {
                                    "name": "empty_nested_sets",
                                    "multiMessageValue": [],
                                },
                            ],
                            "sensitiveParameters": [
                                {"name": "secret", "value": "omit"}
                            ],
                            "resourceIds": ["omit-resource"],
                            "status": {"statusCode": "200"},
                        }
                    ],
                }
            ],
            "next_page_token": "test-page",
        }

    monkeypatch.setattr(
        server,
        "list_drive_audit_activities",
        fake_list_drive_audit_activities,
    )

    result = server.workspace_drive_audit_list(
        max_results=100,
        page_token="test-page",
        user_key="drive@example.com",
        event_name="change_user_access",
        filters="doc_type==document",
        start_time="2026-09-10T00:00:00Z",
        end_time="2026-09-11T00:00:00Z",
        actor_ip_address="198.51.100.12",
        org_unit_id="id:org-unit",
    )

    assert captured == {
        "max_results": 100,
        "page_token": "test-page",
        "user_key": "drive@example.com",
        "event_name": "change_user_access",
        "filters": "doc_type==document",
        "start_time": "2026-09-10T00:00:00Z",
        "end_time": "2026-09-11T00:00:00Z",
        "actor_ip_address": "198.51.100.12",
        "org_unit_id": "id:org-unit",
    }
    assert result == {
        "activities": [
            {
                "occurred_at_epoch_seconds": "123",
                "activity_qualifier": "456",
                "actor": {
                    "email": "actor@example.com",
                    "caller_type": "USER",
                },
                "actor_ip_address": "198.51.100.12",
                "events": [
                    {
                        "event_type": "DRIVE",
                        "event_name": "change_user_access",
                        "primary_event": False,
                        "parameters": [
                            {
                                "parameter_name": "doc_id",
                                "string_value": "doc-123",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "shared_drive_id",
                                "string_value": "drive-123",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "owner_shared_drive_id",
                                "string_value": "owner-drive-123",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "doc_type",
                                "string_value": "document",
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "visibility",
                                "string_value": None,
                                "string_values": [],
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "billable",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": False,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "is_encrypted",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": True,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "owner_is_shared_drive",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": False,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "doc_title",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "target_user",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "unknown_parameter",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "nested",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": [
                                    {"parameter_name": "doc_title"}
                                ],
                                "nested_parameter_sets": None,
                            },
                            {
                                "parameter_name": "empty_nested_sets",
                                "string_value": None,
                                "string_values": None,
                                "integer_value": None,
                                "integer_values": None,
                                "boolean_value": None,
                                "nested_parameters": None,
                                "nested_parameter_sets": [],
                            },
                        ],
                    }
                ],
            }
        ],
        "next_page_token": "test-page",
    }
    serialized = result["activities"][0]
    assert "kind" not in serialized
    assert "etag" not in serialized
    assert "networkInfo" not in serialized
    assert "resourceDetails" not in serialized
    assert "userDeviceInfo" not in serialized
    assert "profileId" not in serialized["actor"]
    assert "applicationInfo" not in serialized["actor"]
    assert "sensitiveParameters" not in str(result)
    assert "omit title" not in str(result)
    assert "omit-target@example.com" not in str(result)
    assert "omit unknown" not in str(result)


def test_workspace_drive_audit_list_uses_safe_default_arguments(monkeypatch):
    captured = {}

    def fake_list_drive_audit_activities(**kwargs):
        captured.update(kwargs)
        return {"activities": [], "next_page_token": None}

    monkeypatch.setattr(
        server,
        "list_drive_audit_activities",
        fake_list_drive_audit_activities,
    )

    assert server.workspace_drive_audit_list() == {
        "activities": [],
        "next_page_token": None,
    }
    assert captured == {
        "max_results": 25,
        "page_token": None,
        "user_key": "all",
        "event_name": None,
        "filters": None,
        "start_time": None,
        "end_time": None,
        "actor_ip_address": None,
        "org_unit_id": None,
    }


def test_drive_audit_serializers_handle_absent_fields():
    assert server._serialize_drive_audit_nested_parameter({}) == {
        "parameter_name": None,
    }
    assert server._serialize_drive_audit_parameter({}) == {
        "parameter_name": None,
        "string_value": None,
        "string_values": None,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": None,
        "nested_parameters": None,
        "nested_parameter_sets": None,
    }
    assert server._serialize_drive_audit_event({}) == {
        "event_type": None,
        "event_name": None,
        "primary_event": None,
        "parameters": [],
    }
    assert server._serialize_drive_audit_activity({}) == {
        "occurred_at_epoch_seconds": None,
        "activity_qualifier": None,
        "actor": {
            "email": None,
            "caller_type": None,
        },
        "actor_ip_address": None,
        "events": [],
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {"max_results": 0},
        {"max_results": 101},
        {"page_token": "  "},
        {"user_key": "\t"},
        {"event_name": ""},
        {"filters": "   "},
        {"start_time": "invalid"},
        {
            "start_time": "2026-09-11T00:00:00Z",
            "end_time": "2026-09-10T00:00:00Z",
        },
    ],
)
def test_workspace_drive_audit_list_rejects_invalid_arguments(
    monkeypatch,
    arguments,
):
    monkeypatch.setattr(
        server,
        "list_drive_audit_activities",
        lambda **kwargs: pytest.fail("A chamada não deveria ocorrer."),
    )

    with pytest.raises(ValueError):
        server.workspace_drive_audit_list(**arguments)
