from mcp.server import MCPServer
from pydantic import StrictInt

from google_workspace_admin.directory.chromeos_devices import (
    list_chromeos_devices,
)
from google_workspace_admin.directory.domains import list_domains
from google_workspace_admin.directory.domain_aliases import list_domain_aliases
from google_workspace_admin.directory.group_members import (
    list_group_members,
)
from google_workspace_admin.directory.groups import list_groups
from google_workspace_admin.directory.mobile_devices import (
    list_mobile_devices,
)
from google_workspace_admin.directory.orgunits import list_orgunits
from google_workspace_admin.directory.role_assignments import (
    list_role_assignments,
)
from google_workspace_admin.directory.roles import list_roles
from google_workspace_admin.directory.resources.buildings import list_buildings
from google_workspace_admin.directory.resources.calendars import (
    list_calendar_resources,
)
from google_workspace_admin.directory.resources.features import (
    list_calendar_features,
)
from google_workspace_admin.directory.users import (
    get_user,
    list_users,
)
from google_workspace_admin.reports.admin_audit import (
    _validate_admin_audit_arguments,
    list_admin_audit_activities,
)
from google_workspace_admin.reports.customer_usage import (
    CUSTOMER_USAGE_ALLOWED_PARAMETERS,
    _validate_customer_usage_arguments,
    get_customer_usage_report,
)
from google_workspace_admin.reports.drive_audit import (
    _validate_drive_audit_arguments,
    list_drive_audit_activities,
)
from google_workspace_admin.reports.login_audit import (
    _validate_login_audit_arguments,
    list_login_audit_activities,
)
from google_workspace_admin.reports.user_usage import (
    _validate_user_usage_arguments,
    get_user_usage_report,
)
from google_workspace_admin.http_errors import (
    PageResult,
    SafeOperationError,
    WorkspaceApiError,
    require_dict_list,
    validate_max_results,
    validate_next_page_token,
    validate_optional_string,
    validate_page_token,
)

mcp = MCPServer(
    name="Google Workspace Admin",
)


def _extract_page(
    page: object,
    item_key: str,
    operation: str,
) -> tuple[list[dict], str | None]:
    if isinstance(page, PageResult):
        items = list(page)
        next_page_token = page.next_page_token
    elif isinstance(page, dict):
        items = page.get(item_key, [])
        next_page_token = page.get("next_page_token")
    elif isinstance(page, list):
        # Compatibilidade com mocks e helpers internos legados.
        items = page
        next_page_token = None
    else:
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
        )

    if not isinstance(items, list) or any(
        not isinstance(item, dict) for item in items
    ):
        raise WorkspaceApiError(
            operation=operation,
            category="malformed_response",
            code="RESPONSE_VALIDATION",
            layer="response",
        )

    return items, validate_next_page_token(next_page_token, operation)


def _serialize_user(user: dict) -> dict:
    """Seleciona os campos de usuário que podem ser expostos pelo MCP."""
    name = user.get("name")
    if not isinstance(name, dict):
        name = {}

    return {
        "id": user.get("id"),
        "primary_email": user.get("primaryEmail"),
        "full_name": name.get("fullName"),
        "given_name": name.get("givenName"),
        "family_name": name.get("familyName"),
        "suspended": user.get("suspended"),
        "archived": user.get("archived"),
        "is_admin": user.get("isAdmin"),
        "is_delegated_admin": user.get("isDelegatedAdmin"),
        "org_unit_path": user.get("orgUnitPath"),
        "creation_time": user.get("creationTime"),
        "last_login_time": user.get("lastLoginTime"),
    }


@mcp.tool()
def workspace_status() -> dict:
    """Retorna o status básico do servidor Google Workspace Admin MCP."""
    return {
        "status": "ok",
        "server": "google-workspace-admin",
        "authentication": "ADC -> IAM signJwt -> DWD",
    }


def _serialize_domain_alias(domain_alias: dict) -> dict:
    """Seleciona os campos de alias de domínio expostos pelo MCP."""
    return {
        "domain_alias_name": domain_alias.get("domainAliasName"),
        "parent_domain_name": domain_alias.get("parentDomainName"),
        "verified": domain_alias.get("verified"),
        "creation_time": domain_alias.get("creationTime"),
    }


@mcp.tool()
def workspace_users_list(
    max_results: StrictInt = 5,
    page_token: str | None = None,
) -> dict:
    """
    Lista usuários do Google Workspace.

    Args:
        max_results: Quantidade máxima de usuários na página.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    try:
        validate_max_results(max_results, 100)
        validate_page_token(page_token)

        page = list_users(
            max_results=max_results,
            page_token=page_token,
        )
        users, next_page_token = _extract_page(
            page,
            "users",
            "Directory users.list",
        )

        return {
            "users": [_serialize_user(user) for user in users],
            "next_page_token": next_page_token,
        }
    except SafeOperationError:
        raise
    except ValueError:
        raise SafeOperationError(
            code="LOCAL_VALIDATION",
            layer="validation",
            operation="users.list",
        ) from None
    except Exception:
        raise SafeOperationError(
            code="UNEXPECTED_LOCAL",
            layer="local",
            operation="users.list",
        ) from None


@mcp.tool()
def workspace_user_get(user_key: str) -> dict:
    """
    Obtém detalhes de um usuário do Google Workspace.

    Args:
        user_key: E-mail principal, alias ou ID do usuário.
    """
    user = get_user(user_key)

    return _serialize_user(user)


def _serialize_group(group: dict) -> dict:
    """Seleciona os campos de grupo que podem ser expostos pelo MCP."""
    return {
        "id": group.get("id"),
        "email": group.get("email"),
        "name": group.get("name"),
        "description": group.get("description"),
        "direct_members_count": group.get("directMembersCount"),
        "admin_created": group.get("adminCreated"),
    }


@mcp.tool()
def workspace_groups_list(
    max_results: StrictInt = 20,
    page_token: str | None = None,
) -> dict:
    """
    Lista grupos do Google Workspace.

    Args:
        max_results: Quantidade máxima de grupos na página.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 200)
    validate_page_token(page_token)

    page = list_groups(
        max_results=max_results,
        page_token=page_token,
    )
    groups, next_page_token = _extract_page(
        page,
        "groups",
        "Directory groups.list",
    )

    return {
        "groups": [_serialize_group(group) for group in groups],
        "next_page_token": next_page_token,
    }


def _serialize_group_member(member: dict) -> dict:
    """Seleciona os campos de membro de grupo que podem ser expostos pelo MCP."""
    return {
        "id": member.get("id"),
        "email": member.get("email"),
        "role": member.get("role"),
        "type": member.get("type"),
        "status": member.get("status"),
        "delivery_settings": member.get("delivery_settings"),
    }


@mcp.tool()
def workspace_group_members_list(
    group_key: str,
    max_results: StrictInt = 200,
    page_token: str | None = None,
) -> dict:
    """
    Lista membros diretos de um grupo do Google Workspace.

    Args:
        group_key: E-mail, alias ou ID imutável do grupo.
        max_results: Quantidade máxima de membros na página.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    if not group_key.strip():
        raise ValueError("group_key não pode estar vazio.")

    validate_max_results(max_results, 200)
    validate_page_token(page_token)

    page = list_group_members(
        group_key=group_key,
        max_results=max_results,
        page_token=page_token,
    )
    members, next_page_token = _extract_page(
        page,
        "members",
        "Directory group members.list",
    )

    return {
        "members": [
            _serialize_group_member(member)
            for member in members
        ],
        "next_page_token": next_page_token,
    }


def _serialize_orgunit(orgunit: dict) -> dict:
    """Seleciona os campos de unidade organizacional expostos pelo MCP."""
    return {
        "org_unit_id": orgunit.get("orgUnitId"),
        "name": orgunit.get("name"),
        "description": orgunit.get("description"),
        "org_unit_path": orgunit.get("orgUnitPath"),
        "parent_org_unit_id": orgunit.get("parentOrgUnitId"),
        "parent_org_unit_path": orgunit.get("parentOrgUnitPath"),
        "block_inheritance": orgunit.get("blockInheritance"),
    }


@mcp.tool()
def workspace_orgunits_list(
    org_unit_path: str = "/",
    org_unit_type: str = "all",
) -> list[dict]:
    """
    Lista unidades organizacionais do Google Workspace.

    Args:
        org_unit_path: Caminho da OU que será a raiz da consulta.
        org_unit_type: Tipo da consulta: all, children ou all_including_parent.
    """
    normalized_path = org_unit_path.strip()
    if not normalized_path:
        raise ValueError("org_unit_path não pode estar vazio.")

    if not normalized_path.startswith("/"):
        raise ValueError("org_unit_path deve começar com '/'.")

    allowed_types = {
        "all",
        "children",
        "all_including_parent",
    }
    if org_unit_type not in allowed_types:
        raise ValueError(
            "org_unit_type deve ser 'all', 'children' "
            "ou 'all_including_parent'."
        )

    orgunits = list_orgunits(
        org_unit_path=normalized_path,
        org_unit_type=org_unit_type,
    )

    return [
        _serialize_orgunit(orgunit)
        for orgunit in orgunits
    ]


def _serialize_mobile_device(device: dict) -> dict:
    """Seleciona os campos de dispositivo móvel expostos pelo MCP."""
    return {
        "resource_id": device.get("resourceId"),
        "device_id": device.get("deviceId"),
        "name": device.get("name"),
        "email": device.get("email"),
        "model": device.get("model"),
        "manufacturer": device.get("manufacturer"),
        "type": device.get("type"),
        "os": device.get("os"),
        "status": device.get("status"),
        "first_sync": device.get("firstSync"),
        "last_sync": device.get("lastSync"),
        "hardware_id": device.get("hardwareId"),
        "serial_number": device.get("serialNumber"),
        "imei": device.get("imei"),
        "meid": device.get("meid"),
        "wifi_mac_address": device.get("wifiMacAddress"),
        "network_operator": device.get("networkOperator"),
        "default_language": device.get("defaultLanguage"),
        "managed_account_is_on_owner_profile": (
            device.get("managedAccountIsOnOwnerProfile")
        ),
    }


@mcp.tool()
def workspace_mobile_devices_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista dispositivos móveis de usuários do Google Workspace.

    Args:
        max_results: Quantidade máxima de dispositivos a retornar.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    page = list_mobile_devices(
        max_results=max_results,
        page_token=page_token,
    )
    devices, next_page_token = _extract_page(
        page,
        "mobile_devices",
        "Directory mobile devices.list",
    )

    return {
        "mobile_devices": [
            _serialize_mobile_device(device)
            for device in devices
        ],
        "next_page_token": next_page_token,
    }


def _serialize_chromeos_device(device: dict) -> dict:
    """Seleciona os campos de dispositivo ChromeOS expostos pelo MCP."""
    return {
        "device_id": device.get("deviceId"),
        "serial_number": device.get("serialNumber"),
        "model": device.get("model"),
        "manufacturer": device.get("manufacturer"),
        "status": device.get("status"),
        "os_version": device.get("osVersion"),
        "platform_version": device.get("platformVersion"),
        "firmware_version": device.get("firmwareVersion"),
        "mac_address": device.get("macAddress"),
        "ethernet_mac_address": device.get("ethernetMacAddress"),
        "org_unit_path": device.get("orgUnitPath"),
        "annotated_user": device.get("annotatedUser"),
        "annotated_location": device.get("annotatedLocation"),
        "annotated_asset_id": device.get("annotatedAssetId"),
        "last_sync": device.get("lastSync"),
        "last_enrollment_time": device.get("lastEnrollmentTime"),
        "support_end_date": device.get("supportEndDate"),
        "notes": device.get("notes"),
    }


@mcp.tool()
def workspace_chromeos_devices_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista dispositivos ChromeOS do Google Workspace.

    Args:
        max_results: Quantidade máxima de dispositivos a retornar.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 300)
    validate_page_token(page_token)

    page = list_chromeos_devices(
        max_results=max_results,
        page_token=page_token,
    )
    devices, next_page_token = _extract_page(
        page,
        "chromeos_devices",
        "Directory chromeos devices.list",
    )

    return {
        "chromeos_devices": [
            _serialize_chromeos_device(device)
            for device in devices
        ],
        "next_page_token": next_page_token,
    }


def _serialize_role(role: dict) -> dict:
    """Seleciona os campos de função administrativa expostos pelo MCP."""
    return {
        "role_id": role.get("roleId"),
        "role_name": role.get("roleName"),
        "role_description": role.get("roleDescription"),
        "role_privileges": role.get("rolePrivileges"),
        "is_system_role": role.get("isSystemRole"),
        "is_super_admin_role": role.get("isSuperAdminRole"),
    }


@mcp.tool()
def workspace_roles_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista funções administrativas do Google Workspace.

    Args:
        max_results: Quantidade máxima de funções a retornar.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    page = list_roles(
        max_results=max_results,
        page_token=page_token,
    )
    roles, next_page_token = _extract_page(
        page,
        "roles",
        "Directory roles.list",
    )

    return {
        "roles": [
            _serialize_role(role)
            for role in roles
        ],
        "next_page_token": next_page_token,
    }


def _serialize_role_assignment(assignment: dict) -> dict:
    """Seleciona os campos de atribuição administrativa expostos pelo MCP."""
    return {
        "role_assignment_id": assignment.get("roleAssignmentId"),
        "role_id": assignment.get("roleId"),
        "assigned_to": assignment.get("assignedTo"),
        "scope_type": assignment.get("scopeType"),
        "org_unit_id": assignment.get("orgUnitId"),
    }


@mcp.tool()
def workspace_role_assignments_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista atribuições de funções administrativas do Google Workspace.

    Args:
        max_results: Quantidade máxima de atribuições a retornar.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    page = list_role_assignments(
        max_results=max_results,
        page_token=page_token,
    )
    assignments, next_page_token = _extract_page(
        page,
        "role_assignments",
        "Directory role assignments.list",
    )

    return {
        "role_assignments": [
            _serialize_role_assignment(assignment)
            for assignment in assignments
        ],
        "next_page_token": next_page_token,
    }


def _serialize_domain(domain: dict) -> dict:
    """Seleciona os campos de domínio expostos pelo MCP."""
    if not isinstance(domain, dict):
        raise WorkspaceApiError(
            operation="Directory domains.list",
            category="malformed_response",
        )

    domain_aliases = require_dict_list(
        domain,
        "domainAliases",
        "Directory domains.list",
    )

    return {
        "domain_name": domain.get("domainName"),
        "verified": domain.get("verified"),
        "is_primary": domain.get("isPrimary"),
        "creation_time": domain.get("creationTime"),
        "domain_aliases": [
            _serialize_domain_alias(domain_alias)
            for domain_alias in domain_aliases
        ],
    }


@mcp.tool()
def workspace_domains_list() -> list[dict]:
    """
    Lista os domínios do Google Workspace.
    """
    domains = list_domains()

    return [
        _serialize_domain(domain)
        for domain in domains
    ]


@mcp.tool()
def workspace_domain_aliases_list(
    parent_domain_name: str | None = None,
) -> list[dict]:
    """
    Lista os aliases de domínio do Google Workspace.

    Quando parent_domain_name é informado, retorna somente os aliases
    associados ao domínio pai especificado.
    """
    validate_optional_string(parent_domain_name, "parent_domain_name")

    domain_aliases = list_domain_aliases(
        parent_domain_name=parent_domain_name
    )

    return [
        _serialize_domain_alias(domain_alias)
        for domain_alias in domain_aliases
    ]


def _serialize_building_address(address: dict | None) -> dict:
    """Seleciona os campos de endereço de edifício expostos pelo MCP."""
    address_data = address or {}

    return {
        "region_code": address_data.get("regionCode"),
        "language_code": address_data.get("languageCode"),
        "postal_code": address_data.get("postalCode"),
        "administrative_area": address_data.get("administrativeArea"),
        "locality": address_data.get("locality"),
        "sublocality": address_data.get("sublocality"),
        "address_lines": address_data.get("addressLines", []),
    }


def _serialize_building(building: dict) -> dict:
    """Seleciona os campos de edifício expostos pelo MCP."""
    coordinates = building.get("coordinates") or {}

    return {
        "building_id": building.get("buildingId"),
        "building_name": building.get("buildingName"),
        "description": building.get("description"),
        "floor_names": building.get("floorNames", []),
        "coordinates": {
            "latitude": coordinates.get("latitude"),
            "longitude": coordinates.get("longitude"),
        },
        "address": _serialize_building_address(
            building.get("address")
        ),
    }


@mcp.tool()
def workspace_buildings_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista uma página de edifícios dos recursos corporativos do Workspace.

    Args:
        max_results: Quantidade máxima de edifícios na página.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 500)
    validate_page_token(page_token)

    page = list_buildings(
        max_results=max_results,
        page_token=page_token,
    )

    buildings, next_page_token = _extract_page(
        page,
        "buildings",
        "Directory buildings.list",
    )

    return {
        "buildings": [
            _serialize_building(building)
            for building in buildings
        ],
        "next_page_token": next_page_token,
    }


def _serialize_calendar_resource(resource: dict) -> dict:
    """Seleciona os campos de recurso corporativo expostos pelo MCP."""
    return {
        "resource_id": resource.get("resourceId"),
        "resource_name": resource.get("resourceName"),
        "resource_description": resource.get("resourceDescription"),
        "resource_type": resource.get("resourceType"),
        "resource_email": resource.get("resourceEmail"),
        "resource_category": resource.get("resourceCategory"),
        "user_visible_description": resource.get(
            "userVisibleDescription"
        ),
        "generated_resource_name": resource.get(
            "generatedResourceName"
        ),
        "capacity": resource.get("capacity"),
        "building_id": resource.get("buildingId"),
        "floor_name": resource.get("floorName"),
        "floor_section": resource.get("floorSection"),
    }


@mcp.tool()
def workspace_calendar_resources_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
    order_by: str | None = None,
    query: str | None = None,
) -> dict:
    """
    Lista uma página de recursos corporativos de Calendar do Workspace.

    Args:
        max_results: Quantidade máxima de recursos na página.
        page_token: Token opaco de continuação retornado pela página anterior.
        order_by: Ordenação oficial da Directory API para os recursos.
        query: Filtro oficial da Directory API para os recursos.
    """
    validate_max_results(max_results, 500)
    validate_page_token(page_token)

    validate_optional_string(order_by, "order_by")
    validate_optional_string(query, "query")

    page = list_calendar_resources(
        max_results=max_results,
        page_token=page_token,
        order_by=order_by,
        query=query,
    )

    resources, next_page_token = _extract_page(
        page,
        "resources",
        "Directory resources.calendars.list",
    )

    return {
        "resources": [
            _serialize_calendar_resource(resource)
            for resource in resources
        ],
        "next_page_token": next_page_token,
    }


def _serialize_calendar_feature(feature: dict) -> dict:
    """Seleciona os campos de feature de Calendar expostos pelo MCP."""
    return {
        "feature_name": feature.get("name"),
    }


@mcp.tool()
def workspace_calendar_features_list(
    max_results: StrictInt = 100,
    page_token: str | None = None,
) -> dict:
    """
    Lista uma página de features dos recursos corporativos de Calendar.

    Args:
        max_results: Quantidade máxima de features na página.
        page_token: Token opaco de continuação retornado pela página anterior.
    """
    validate_max_results(max_results, 500)
    validate_page_token(page_token)

    page = list_calendar_features(
        max_results=max_results,
        page_token=page_token,
    )

    features, next_page_token = _extract_page(
        page,
        "features",
        "Directory resources.features.list",
    )

    return {
        "features": [
            _serialize_calendar_feature(feature)
            for feature in features
        ],
        "next_page_token": next_page_token,
    }


def _serialize_admin_audit_nested_parameter(parameter: dict) -> dict:
    """Serializa um parâmetro aninhado de atividade administrativa."""
    return {
        "parameter_name": parameter.get("name"),
        "string_value": parameter.get("value"),
        "string_values": parameter.get("multiValue"),
        "integer_value": parameter.get("intValue"),
        "integer_values": parameter.get("multiIntValue"),
        "boolean_value": parameter.get("boolValue"),
    }


def _serialize_admin_audit_parameter(parameter: dict) -> dict:
    """Serializa um parâmetro não sensível de atividade administrativa."""
    message_value = parameter.get("messageValue")
    multi_message_value = parameter.get("multiMessageValue")

    return {
        "parameter_name": parameter.get("name"),
        "string_value": parameter.get("value"),
        "string_values": parameter.get("multiValue"),
        "integer_value": parameter.get("intValue"),
        "integer_values": parameter.get("multiIntValue"),
        "boolean_value": parameter.get("boolValue"),
        "nested_parameters": (
            [
                _serialize_admin_audit_nested_parameter(nested_parameter)
                for nested_parameter in message_value.get("parameter", [])
            ]
            if message_value is not None
            else None
        ),
        "nested_parameter_sets": (
            [
                [
                    _serialize_admin_audit_nested_parameter(
                        nested_parameter
                    )
                    for nested_parameter in message_set.get("parameter", [])
                ]
                for message_set in multi_message_value
            ]
            if multi_message_value is not None
            else None
        ),
    }


def _serialize_admin_audit_event(event: dict) -> dict:
    """Serializa um evento de atividade administrativa."""
    return {
        "event_type": event.get("type"),
        "event_name": event.get("name"),
        "parameters": [
            _serialize_admin_audit_parameter(parameter)
            for parameter in event.get("parameters", [])
        ],
    }


def _serialize_admin_audit_activity(activity: dict) -> dict:
    """Seleciona os campos seguros de uma atividade administrativa."""
    activity_id = activity.get("id") or {}
    actor = activity.get("actor") or {}

    return {
        "occurred_at_epoch_seconds": activity_id.get("time"),
        "activity_qualifier": activity_id.get("uniqueQualifier"),
        "actor": {
            "email": actor.get("email"),
            "caller_type": actor.get("callerType"),
        },
        "actor_ip_address": activity.get("ipAddress"),
        "events": [
            _serialize_admin_audit_event(event)
            for event in activity.get("events", [])
        ],
    }


@mcp.tool()
def workspace_admin_audit_list(
    max_results: StrictInt = 25,
    page_token: str | None = None,
    user_key: str = "all",
    event_name: str | None = None,
    filters: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    actor_ip_address: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Lista uma página de atividades administrativas do Workspace."""
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    _validate_admin_audit_arguments(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    page = list_admin_audit_activities(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    activities, next_page_token = _extract_page(
        page,
        "activities",
        "Reports admin activities.list",
    )

    return {
        "activities": [
            _serialize_admin_audit_activity(activity)
            for activity in activities
        ],
        "next_page_token": next_page_token,
    }


_LOGIN_SAFE_STRING_PARAMETERS = {
    "login_type",
    "login_challenge_method",
    "login_challenge_status",
}
_LOGIN_SAFE_BOOLEAN_PARAMETERS = {
    "is_suspicious",
    "is_second_factor",
}


def _serialize_login_audit_nested_parameter(parameter: dict) -> dict:
    """Serializa apenas o nome de um parâmetro aninhado de Login Audit."""
    return {
        "parameter_name": parameter.get("name"),
    }


def _serialize_login_audit_parameter(parameter: dict) -> dict:
    """Serializa parâmetros de Login Audit conforme a allowlist segura."""
    parameter_name = parameter.get("name")
    message_value = parameter.get("messageValue")
    multi_message_value = parameter.get("multiMessageValue")

    string_value = (
        parameter.get("value")
        if parameter_name in _LOGIN_SAFE_STRING_PARAMETERS
        else None
    )
    string_values = (
        parameter.get("multiValue")
        if parameter_name in _LOGIN_SAFE_STRING_PARAMETERS
        else None
    )
    boolean_value = (
        parameter.get("boolValue")
        if parameter_name in _LOGIN_SAFE_BOOLEAN_PARAMETERS
        else None
    )

    return {
        "parameter_name": parameter_name,
        "string_value": string_value,
        "string_values": string_values,
        "integer_value": None,
        "integer_values": None,
        "boolean_value": boolean_value,
        "nested_parameters": (
            [
                _serialize_login_audit_nested_parameter(nested_parameter)
                for nested_parameter in message_value.get("parameter", [])
            ]
            if message_value is not None
            else None
        ),
        "nested_parameter_sets": (
            [
                [
                    _serialize_login_audit_nested_parameter(
                        nested_parameter
                    )
                    for nested_parameter in message_set.get("parameter", [])
                ]
                for message_set in multi_message_value
            ]
            if multi_message_value is not None
            else None
        ),
    }


def _serialize_login_audit_event(event: dict) -> dict:
    """Serializa um evento de Login Audit sem payload bruto."""
    return {
        "event_type": event.get("type"),
        "event_name": event.get("name"),
        "parameters": [
            _serialize_login_audit_parameter(parameter)
            for parameter in event.get("parameters", [])
        ],
    }


def _serialize_login_audit_activity(activity: dict) -> dict:
    """Seleciona campos administrativos seguros de uma atividade de login."""
    activity_id = activity.get("id") or {}
    actor = activity.get("actor") or {}

    return {
        "occurred_at_epoch_seconds": activity_id.get("time"),
        "activity_qualifier": activity_id.get("uniqueQualifier"),
        "actor": {
            "email": actor.get("email"),
            "caller_type": actor.get("callerType"),
        },
        "actor_ip_address": activity.get("ipAddress"),
        "events": [
            _serialize_login_audit_event(event)
            for event in activity.get("events", [])
        ],
    }


@mcp.tool()
def workspace_login_audit_list(
    max_results: StrictInt = 25,
    page_token: str | None = None,
    user_key: str = "all",
    event_name: str | None = None,
    filters: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    actor_ip_address: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Lista uma página segura de atividades de Login Audit do Workspace."""
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    _validate_login_audit_arguments(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    page = list_login_audit_activities(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    activities, next_page_token = _extract_page(
        page,
        "activities",
        "Reports login activities.list",
    )

    return {
        "activities": [
            _serialize_login_audit_activity(activity)
            for activity in activities
        ],
        "next_page_token": next_page_token,
    }


_DRIVE_SAFE_STRING_PARAMETERS = {
    "doc_type",
    "visibility",
    "deletion_reason",
    "membership_change_type",
    "added_role",
    "removed_role",
}
_DRIVE_SAFE_ID_PARAMETERS = {
    "doc_id",
    "shared_drive_id",
    "owner_shared_drive_id",
}
_DRIVE_SAFE_BOOLEAN_PARAMETERS = {
    "billable",
    "is_encrypted",
    "owner_is_shared_drive",
    "primary_event",
}


def _serialize_drive_audit_nested_parameter(parameter: dict) -> dict:
    """Preserva somente o nome de parâmetros aninhados do Drive Audit."""
    return {
        "parameter_name": parameter.get("name"),
    }


def _serialize_drive_audit_parameter(parameter: dict) -> dict:
    """Serializa parâmetros do Drive Audit conforme uma allowlist explícita."""
    parameter_name = parameter.get("name")
    message_value = parameter.get("messageValue")
    multi_message_value = parameter.get("multiMessageValue")
    safe_value_parameter = (
        parameter_name in _DRIVE_SAFE_STRING_PARAMETERS
        or parameter_name in _DRIVE_SAFE_ID_PARAMETERS
    )

    return {
        "parameter_name": parameter_name,
        "string_value": (
            parameter.get("value")
            if safe_value_parameter
            else None
        ),
        "string_values": (
            parameter.get("multiValue")
            if safe_value_parameter
            else None
        ),
        "integer_value": None,
        "integer_values": None,
        "boolean_value": (
            parameter.get("boolValue")
            if parameter_name in _DRIVE_SAFE_BOOLEAN_PARAMETERS
            else None
        ),
        "nested_parameters": (
            [
                _serialize_drive_audit_nested_parameter(nested_parameter)
                for nested_parameter in message_value.get("parameter", [])
            ]
            if message_value is not None
            else None
        ),
        "nested_parameter_sets": (
            [
                [
                    _serialize_drive_audit_nested_parameter(
                        nested_parameter
                    )
                    for nested_parameter in message_set.get("parameter", [])
                ]
                for message_set in multi_message_value
            ]
            if multi_message_value is not None
            else None
        ),
    }


def _serialize_drive_audit_event(event: dict) -> dict:
    """Serializa um evento Drive sem payload ou estruturas desconhecidas."""
    primary_event = event.get("primaryEvent")
    if primary_event is None:
        for parameter in event.get("parameters", []):
            if (
                parameter.get("name") == "primary_event"
                and "boolValue" in parameter
            ):
                primary_event = parameter.get("boolValue")
                break

    return {
        "event_type": event.get("type"),
        "event_name": event.get("name"),
        "primary_event": primary_event,
        "parameters": [
            _serialize_drive_audit_parameter(parameter)
            for parameter in event.get("parameters", [])
        ],
    }


def _serialize_drive_audit_activity(activity: dict) -> dict:
    """Seleciona campos administrativos seguros de uma atividade Drive."""
    activity_id = activity.get("id") or {}
    actor = activity.get("actor") or {}

    return {
        "occurred_at_epoch_seconds": activity_id.get("time"),
        "activity_qualifier": activity_id.get("uniqueQualifier"),
        "actor": {
            "email": actor.get("email"),
            "caller_type": actor.get("callerType"),
        },
        "actor_ip_address": activity.get("ipAddress"),
        "events": [
            _serialize_drive_audit_event(event)
            for event in activity.get("events", [])
        ],
    }


@mcp.tool()
def workspace_drive_audit_list(
    max_results: StrictInt = 25,
    page_token: str | None = None,
    user_key: str = "all",
    event_name: str | None = None,
    filters: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    actor_ip_address: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Lista uma página segura de atividades de Drive Audit do Workspace."""
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    _validate_drive_audit_arguments(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    page = list_drive_audit_activities(
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        event_name=event_name,
        filters=filters,
        start_time=start_time,
        end_time=end_time,
        actor_ip_address=actor_ip_address,
        org_unit_id=org_unit_id,
    )

    activities, next_page_token = _extract_page(
        page,
        "activities",
        "Reports drive activities.list",
    )

    return {
        "activities": [
            _serialize_drive_audit_activity(activity)
            for activity in activities
        ],
        "next_page_token": next_page_token,
    }


_USER_USAGE_INTEGER_PARAMETERS = {
    "accounts:drive_used_quota_in_mb",
    "accounts:gmail_used_quota_in_mb",
    "accounts:num_authorized_apps",
    "accounts:num_passkeys_enrolled",
    "accounts:num_roles_assigned",
    "accounts:num_security_keys",
    "accounts:total_quota_in_mb",
    "accounts:used_quota_in_mb",
    "accounts:used_quota_in_percentage",
    "chat:num_28day_attachments_uploaded",
    "chat:num_28day_conversations_read",
    "chat:num_28day_messages_and_reactions_sent",
    "chat:num_28day_spaces_created",
    "classroom:num_courses_created",
    "classroom:num_posts_created",
    "docs:num_docs",
    "docs:num_docs_edited",
    "docs:num_docs_not_edited_for_3months",
    "docs:num_docs_not_edited_for_6months",
    "docs:num_docs_not_edited_for_12months",
    "docs:num_docs_not_viewed_for_3months",
    "docs:num_docs_not_viewed_for_6months",
    "docs:num_docs_not_viewed_for_12months",
    "docs:num_docs_shared_outside_domain",
    "docs:num_docs_viewed",
    "docs:num_docs_with_visibility_anyone_with_link",
    "docs:num_docs_with_visibility_people_at_domain",
    "docs:num_docs_with_visibility_people_at_domain_with_link",
    "docs:num_docs_with_visibility_private",
    "docs:num_docs_with_visibility_public",
    "docs:num_docs_externally_visible",
    "docs:num_docs_internally_visible",
    "docs:num_drawings",
    "docs:num_drawings_edited",
    "docs:num_drawings_viewed",
    "docs:num_forms",
    "docs:num_forms_edited",
    "docs:num_forms_viewed",
    "docs:num_presentations",
    "docs:num_presentations_edited",
    "docs:num_presentations_viewed",
    "docs:num_shared_docs",
    "docs:num_spreadsheets",
    "docs:num_spreadsheets_edited",
    "docs:num_spreadsheets_viewed",
    "docs:num_text_documents",
    "docs:num_text_documents_edited",
    "docs:num_text_documents_viewed",
    "docs:num_uploaded_files",
    "docs:num_uploaded_files_edited",
    "docs:num_uploaded_files_viewed",
    "gmail:num_emails_exchanged",
    "gmail:num_emails_received",
    "gmail:num_emails_sent",
    "gmail:num_spam_emails_received",
}
_USER_USAGE_BOOLEAN_PARAMETERS = {
    "accounts:disabled",
    "accounts:is_2sv_enforced",
    "accounts:is_2sv_enrolled",
    "accounts:is_2sv_protected",
    "accounts:is_archived",
    "accounts:is_suspended",
    "gmail:is_gmail_enabled",
}
_USER_USAGE_DATETIME_PARAMETERS = {
    "accounts:timestamp_creation",
    "accounts:timestamp_last_login",
    "accounts:timestamp_last_sso",
}
_USER_USAGE_PARAMETER_TYPES = {
    **{
        parameter_name: "integer"
        for parameter_name in _USER_USAGE_INTEGER_PARAMETERS
    },
    **{
        parameter_name: "boolean"
        for parameter_name in _USER_USAGE_BOOLEAN_PARAMETERS
    },
    **{
        parameter_name: "datetime"
        for parameter_name in _USER_USAGE_DATETIME_PARAMETERS
    },
}


def _canonical_user_usage_parameter_name(name: object) -> str | None:
    if not isinstance(name, str) or not name.strip():
        return None

    normalized_name = name.strip()
    if ":" not in normalized_name:
        account_name = f"accounts:{normalized_name}"
        if account_name in _USER_USAGE_PARAMETER_TYPES:
            return account_name
        return normalized_name

    application, parameter_name = normalized_name.split(":", 1)
    return f"{application.lower()}:{parameter_name}"


def _requested_user_usage_parameters(parameters: str | None) -> set[str]:
    if parameters is None:
        return set()

    return {
        canonical_name
        for requested_name in parameters.split(",")
        if (
            canonical_name := _canonical_user_usage_parameter_name(
                requested_name
            )
        ) is not None
    }


def _serialize_user_usage_parameter(
    parameter: dict,
    requested_parameters: set[str],
) -> dict | None:
    if not isinstance(parameter, dict):
        return None

    parameter_name = parameter.get("name")
    canonical_name = _canonical_user_usage_parameter_name(parameter_name)
    parameter_type = _USER_USAGE_PARAMETER_TYPES.get(canonical_name)
    if parameter_type is None:
        return None

    if (
        parameter_type == "datetime"
        and canonical_name not in requested_parameters
    ):
        return None

    output_name = parameter_name.strip()
    if parameter_type == "integer":
        value = parameter.get("intValue")
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return {
            "parameter_name": output_name,
            "integer_value": value,
        }

    if parameter_type == "boolean":
        value = parameter.get("boolValue")
        if not isinstance(value, bool):
            return None
        return {
            "parameter_name": output_name,
            "boolean_value": value,
        }

    value = parameter.get("datetimeValue")
    if not isinstance(value, str) or not value:
        return None
    return {
        "parameter_name": output_name,
        "datetime_value": value,
    }


def _serialize_user_usage_report(
    usage_report: dict,
    requested_parameters: set[str],
) -> dict:
    entity = usage_report.get("entity")
    if not isinstance(entity, dict):
        entity = {}

    raw_parameters = usage_report.get("parameters", [])
    if not isinstance(raw_parameters, list):
        raw_parameters = []

    return {
        "date": usage_report.get("date"),
        "profile_id": entity.get("profileId"),
        "parameters": [
            serialized_parameter
            for parameter in raw_parameters
            if (
                serialized_parameter := _serialize_user_usage_parameter(
                    parameter,
                    requested_parameters,
                )
            ) is not None
        ],
    }


def _serialize_user_usage_page(
    page: dict,
    parameters: str | None,
) -> dict:
    requested_parameters = _requested_user_usage_parameters(parameters)
    raw_usage_reports = page.get("usage_reports", [])
    if not isinstance(raw_usage_reports, list):
        raw_usage_reports = []

    warnings_present = page.get("warnings_present")
    if not isinstance(warnings_present, bool):
        warnings_present = False

    warnings_count = page.get("warnings_count")
    if (
        isinstance(warnings_count, bool)
        or not isinstance(warnings_count, int)
        or warnings_count < 0
    ):
        warnings_count = 0

    return {
        "usage_reports": [
            _serialize_user_usage_report(
                usage_report,
                requested_parameters,
            )
            for usage_report in raw_usage_reports
            if isinstance(usage_report, dict)
        ],
        "next_page_token": page.get("next_page_token"),
        "warnings_present": warnings_present,
        "warnings_count": warnings_count,
    }


@mcp.tool()
def workspace_user_usage_get(
    date: str,
    max_results: StrictInt = 25,
    page_token: str | None = None,
    user_key: str = "all",
    parameters: str | None = None,
    filters: str | None = None,
    org_unit_id: str | None = None,
) -> dict:
    """Obtém uma página sanitizada de User Usage Report do Workspace."""
    validate_max_results(max_results, 100)
    validate_page_token(page_token)

    _validate_user_usage_arguments(
        date=date,
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        parameters=parameters,
        filters=filters,
        org_unit_id=org_unit_id,
    )

    page = get_user_usage_report(
        date=date,
        max_results=max_results,
        page_token=page_token,
        user_key=user_key,
        parameters=parameters,
        filters=filters,
        org_unit_id=org_unit_id,
    )

    usage_reports, next_page_token = _extract_page(
        page,
        "usage_reports",
        "Reports user usage.get",
    )
    normalized_page = {
        **page,
        "usage_reports": usage_reports,
        "next_page_token": next_page_token,
    }

    return _serialize_user_usage_page(normalized_page, parameters)


def _serialize_customer_usage_parameter(
    parameter: dict,
    requested_parameters: set[str],
) -> dict | None:
    if not isinstance(parameter, dict):
        return None

    parameter_name = parameter.get("name")
    if (
        not isinstance(parameter_name, str)
        or parameter_name not in requested_parameters
        or parameter_name not in CUSTOMER_USAGE_ALLOWED_PARAMETERS
    ):
        return None

    value = parameter.get("intValue")
    if isinstance(value, bool) or not isinstance(value, int):
        return None

    return {
        "parameter_name": parameter_name,
        "integer_value": value,
    }


def _serialize_customer_usage_report(
    usage_report: dict,
    requested_parameters: set[str],
) -> dict | None:
    if not isinstance(usage_report, dict):
        return None

    report_date = usage_report.get("date")
    if not isinstance(report_date, str) or not report_date:
        return None

    raw_parameters = usage_report.get("parameters", [])
    if not isinstance(raw_parameters, list):
        raw_parameters = []

    return {
        "date": report_date,
        "parameters": [
            serialized_parameter
            for parameter in raw_parameters
            if (
                serialized_parameter := _serialize_customer_usage_parameter(
                    parameter,
                    requested_parameters,
                )
            ) is not None
        ],
    }


def _serialize_customer_usage_page(
    page: dict,
    parameters: str,
) -> dict:
    requested_parameters = set(parameters.split(","))
    raw_usage_reports = page.get("usage_reports", [])
    if not isinstance(raw_usage_reports, list):
        raw_usage_reports = []

    serialized_usage_reports = [
        serialized_report
        for usage_report in raw_usage_reports
        if (
            serialized_report := _serialize_customer_usage_report(
                usage_report,
                requested_parameters,
            )
        ) is not None
    ]

    next_page_token = page.get("next_page_token")
    if not isinstance(next_page_token, str) or not next_page_token:
        next_page_token = None

    warnings_present = page.get("warnings_present")
    if not isinstance(warnings_present, bool):
        warnings_present = False

    warnings_count = page.get("warnings_count")
    if (
        isinstance(warnings_count, bool)
        or not isinstance(warnings_count, int)
        or warnings_count < 0
    ):
        warnings_count = 0

    return {
        "usage_reports": serialized_usage_reports,
        "next_page_token": next_page_token,
        "warnings_present": warnings_present,
        "warnings_count": warnings_count,
    }


@mcp.tool()
def workspace_customer_usage_get(
    date: str,
    parameters: str,
    page_token: str | None = None,
) -> dict:
    """Obtém uma página sanitizada de Customer Usage Report."""
    validate_page_token(page_token)

    normalized_parameters = _validate_customer_usage_arguments(
        date=date,
        parameters=parameters,
        page_token=page_token,
    )

    page = get_customer_usage_report(
        date=date,
        parameters=normalized_parameters,
        page_token=page_token,
    )

    usage_reports, next_page_token = _extract_page(
        page,
        "usage_reports",
        "Reports customer usage.get",
    )
    normalized_page = {
        **page,
        "usage_reports": usage_reports,
        "next_page_token": next_page_token,
    }

    return _serialize_customer_usage_page(
        normalized_page,
        normalized_parameters,
    )


if __name__ == "__main__":
    mcp.run()
