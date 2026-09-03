import google.auth
from google.auth.transport.requests import Request


CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


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
