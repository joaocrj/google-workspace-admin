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
