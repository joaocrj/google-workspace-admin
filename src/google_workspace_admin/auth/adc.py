from collections.abc import Mapping
import json
import os
from pathlib import Path

import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
ADC_FILE_NOT_FOUND = "ADC_FILE_NOT_FOUND"
ADC_TYPE_UNSUPPORTED = "ADC_TYPE_UNSUPPORTED"
ADC_FILE_INVALID = "ADC_FILE_INVALID"
ADC_CONFIGURATION_UNSUPPORTED = "ADC_CONFIGURATION_UNSUPPORTED"
_AUTHORIZED_USER_TOKEN_URI = "https://oauth2.googleapis.com/token"


class ADCLoadError(RuntimeError):
    """Closed, secret-safe error raised by the explicit local ADC loader."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def get_adc_credentials():
    """
    Obtém Application Default Credentials (ADC) do ambiente local.

    Nenhuma Service Account Key é utilizada.
    """
    credentials, project_id = google.auth.default(
        scopes=[CLOUD_PLATFORM_SCOPE]
    )

    if not credentials.valid:
        credentials.refresh(Request())

    return credentials, project_id


def load_local_authorized_user_adc_no_subprocess(
    environ: Mapping[str, str] | None = None,
) -> tuple[Credentials, None]:
    """Load the standard Windows ADC file without credential discovery.

    Only ``APPDATA`` is consulted. The file must contain an authorized-user
    credential and is parsed once in memory. This function never refreshes.
    """

    try:
        if environ is None:
            appdata = os.environ.get("APPDATA")
        elif isinstance(environ, Mapping):
            appdata = environ.get("APPDATA")
        else:
            raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED)
    except ADCLoadError:
        raise
    except Exception:
        raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED) from None

    if (
        not isinstance(appdata, str)
        or not appdata
        or appdata != appdata.strip()
        or "\x00" in appdata
    ):
        raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED)

    try:
        appdata_path = Path(appdata)
        if not appdata_path.is_absolute():
            raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED)
        adc_path = appdata_path / "gcloud" / "application_default_credentials.json"
    except (OSError, TypeError, ValueError):
        raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED) from None

    try:
        serialized_info = adc_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ADCLoadError(ADC_FILE_NOT_FOUND) from None
    except (OSError, UnicodeError, ValueError):
        raise ADCLoadError(ADC_FILE_INVALID) from None

    try:
        info = json.loads(serialized_info)
    except (json.JSONDecodeError, RecursionError):
        raise ADCLoadError(ADC_FILE_INVALID) from None

    if not isinstance(info, dict):
        raise ADCLoadError(ADC_FILE_INVALID)
    credential_type = info.get("type")
    if not isinstance(credential_type, str) or credential_type != "authorized_user":
        raise ADCLoadError(ADC_TYPE_UNSUPPORTED)
    if info.get("token_uri", _AUTHORIZED_USER_TOKEN_URI) != _AUTHORIZED_USER_TOKEN_URI:
        raise ADCLoadError(ADC_CONFIGURATION_UNSUPPORTED)

    try:
        credentials = Credentials.from_authorized_user_info(info)
    except Exception:
        raise ADCLoadError(ADC_FILE_INVALID) from None

    return credentials, None
