from mcp.server import MCPServer

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
from google_workspace_admin.directory.users import (
    get_user,
    list_users,
)

mcp = MCPServer(
    name="Google Workspace Admin",
)


def _serialize_user(user: dict) -> dict:
    """Seleciona os campos de usuário que podem ser expostos pelo MCP."""
    return {
        "id": user.get("id"),
        "primary_email": user.get("primaryEmail"),
        "full_name": user.get("name", {}).get("fullName"),
        "given_name": user.get("name", {}).get("givenName"),
        "family_name": user.get("name", {}).get("familyName"),
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
def workspace_users_list(max_results: int = 5) -> list[dict]:
    """
    Lista usuários do Google Workspace.

    Args:
        max_results: Quantidade máxima de usuários a retornar.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    users = list_users(max_results=max_results)

    return [_serialize_user(user) for user in users]


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
def workspace_groups_list(max_results: int = 20) -> list[dict]:
    """
    Lista grupos do Google Workspace.

    Args:
        max_results: Quantidade máxima de grupos a retornar.
    """
    if max_results < 1 or max_results > 200:
        raise ValueError("max_results deve estar entre 1 e 200.")

    groups = list_groups(max_results=max_results)

    return [_serialize_group(group) for group in groups]


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
    max_results: int = 200,
) -> list[dict]:
    """
    Lista membros diretos de um grupo do Google Workspace.

    Args:
        group_key: E-mail, alias ou ID imutável do grupo.
        max_results: Quantidade máxima de membros a retornar.
    """
    if not group_key.strip():
        raise ValueError("group_key não pode estar vazio.")

    if max_results < 1 or max_results > 200:
        raise ValueError("max_results deve estar entre 1 e 200.")

    members = list_group_members(
        group_key=group_key,
        max_results=max_results,
    )

    return [
        _serialize_group_member(member)
        for member in members
    ]


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
    max_results: int = 100,
) -> list[dict]:
    """
    Lista dispositivos móveis de usuários do Google Workspace.

    Args:
        max_results: Quantidade máxima de dispositivos a retornar.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    devices = list_mobile_devices(
        max_results=max_results,
    )

    return [
        _serialize_mobile_device(device)
        for device in devices
    ]


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
    max_results: int = 100,
) -> list[dict]:
    """
    Lista dispositivos ChromeOS do Google Workspace.

    Args:
        max_results: Quantidade máxima de dispositivos a retornar.
    """
    if max_results < 1 or max_results > 300:
        raise ValueError("max_results deve estar entre 1 e 300.")

    devices = list_chromeos_devices(
        max_results=max_results,
    )

    return [
        _serialize_chromeos_device(device)
        for device in devices
    ]


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
    max_results: int = 100,
) -> list[dict]:
    """
    Lista funções administrativas do Google Workspace.

    Args:
        max_results: Quantidade máxima de funções a retornar.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    roles = list_roles(
        max_results=max_results,
    )

    return [
        _serialize_role(role)
        for role in roles
    ]


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
    max_results: int = 100,
) -> list[dict]:
    """
    Lista atribuições de funções administrativas do Google Workspace.

    Args:
        max_results: Quantidade máxima de atribuições a retornar.
    """
    if max_results < 1 or max_results > 100:
        raise ValueError("max_results deve estar entre 1 e 100.")

    assignments = list_role_assignments(
        max_results=max_results,
    )

    return [
        _serialize_role_assignment(assignment)
        for assignment in assignments
    ]


def _serialize_domain(domain: dict) -> dict:
    """Seleciona os campos de domínio expostos pelo MCP."""
    return {
        "domain_name": domain.get("domainName"),
        "verified": domain.get("verified"),
        "is_primary": domain.get("isPrimary"),
        "creation_time": domain.get("creationTime"),
        "domain_aliases": domain.get("domainAliases", []),
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
    domain_aliases = list_domain_aliases(
        parent_domain_name=parent_domain_name
    )

    return [
        _serialize_domain_alias(domain_alias)
        for domain_alias in domain_aliases
    ]

if __name__ == "__main__":
    mcp.run()