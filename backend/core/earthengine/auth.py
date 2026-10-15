import os
import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("geoharvest.earthengine.auth")

try:
    import ee
    import ee.oauth
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False
    ee = None


def check_ee_available() -> bool:
    """Dynamically checks and loads Earth Engine if not already imported."""
    global ee, EE_AVAILABLE
    if EE_AVAILABLE and ee is not None:
        return True
    try:
        import ee as _ee
        import ee.oauth
        ee = _ee
        EE_AVAILABLE = True
        return True
    except (ImportError, Exception):
        EE_AVAILABLE = False
        return False


class EarthEngineAuthManager:
    """
    Manages Google Earth Engine authentication workflows including:
    - Interactive OAuth verification with Google Earth Engine client-auth page
    - Google Cloud Project ID association and verification
    - Service Account JSON key authentication
    - Live connectivity testing and credential status checking
    """

    def __init__(self):
        self._auth_sessions: Dict[str, Dict[str, Any]] = {}
        self._active_project: Optional[str] = None
        self._is_initialized = False

    @property
    def credentials_path(self) -> Path:
        if check_ee_available() and hasattr(ee, "oauth") and hasattr(ee.oauth, "get_credentials_path"):
            try:
                return Path(ee.oauth.get_credentials_path())
            except Exception:
                pass
        return Path.home() / ".config" / "earthengine" / "credentials"

    def get_stored_project_id(self) -> Optional[str]:
        """Retrieves stored project ID from environment or credentials file."""
        # 1. Environment variable
        env_proj = os.environ.get("GEOHARVEST_EE_PROJECT") or os.environ.get("EARTHENGINE_PROJECT")
        if env_proj and env_proj.strip():
            return env_proj.strip()

        # 2. Earth Engine credentials file
        cred_path = self.credentials_path
        if cred_path.exists():
            try:
                data = json.loads(cred_path.read_text(encoding="utf-8"))
                proj = data.get("project")
                if proj and str(proj).strip():
                    return str(proj).strip()
            except Exception as e:
                logger.warning(f"Failed to read project from credentials file: {e}")

        return None

    def generate_auth_url(self) -> Dict[str, Any]:
        """
        Initiates the official Earth Engine notebook/client-auth flow.
        Generates verification URL that sends users to Google's authentication page.
        """
        if not check_ee_available():
            raise RuntimeError("earthengine-api package is not installed.")

        # Clean expired sessions (> 15 minutes)
        now = time.time()
        self._auth_sessions = {
            sid: sess for sid, sess in self._auth_sessions.items()
            if now - sess["created_at"] < 900
        }

        session_id = str(uuid.uuid4())
        try:
            flow = ee.oauth.Flow("notebook")
            auth_url = flow.auth_url
            code_verifier = flow.code_verifier

            self._auth_sessions[session_id] = {
                "created_at": now,
                "code_verifier": code_verifier,
                "auth_url": auth_url,
            }

            return {
                "session_id": session_id,
                "auth_url": auth_url,
                "expires_in_seconds": 900,
                "auth_page_url": "https://code.earthengine.google.com/client-auth",
            }
        except Exception as e:
            logger.error(f"Failed to generate GEE auth URL: {e}", exc_info=True)
            raise RuntimeError(f"Could not generate Earth Engine auth URL: {str(e)}")

    def exchange_code(
        self,
        auth_code: str,
        session_id: Optional[str] = None,
        code_verifier: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Exchanges the authorization code obtained from Google for permanent refresh tokens.
        """
        if not check_ee_available():
            raise RuntimeError("earthengine-api package is not installed.")

        auth_code = auth_code.strip()
        if not auth_code:
            raise ValueError("Authorization code is required.")

        # Resolve code_verifier
        verifier = code_verifier
        if not verifier and session_id and session_id in self._auth_sessions:
            verifier = self._auth_sessions[session_id]["code_verifier"]

        try:
            # Exchange code and write token to ~/.config/earthengine/credentials
            ee.oauth._obtain_and_write_token(auth_code=auth_code, code_verifier=verifier)
            logger.info("Successfully obtained and saved GEE OAuth token.")

            # If project_id provided, record it
            if project_id and project_id.strip():
                self.set_project_id(project_id.strip())

            # Test initialization
            status = self.get_status()
            return {
                "success": True,
                "message": "Earth Engine credentials successfully authorized and saved.",
                "status": status,
            }
        except Exception as e:
            logger.error(f"Failed to exchange GEE authorization code: {e}", exc_info=True)
            raise RuntimeError(f"Authorization code exchange failed: {str(e)}")

    def set_project_id(self, project_id: str) -> Dict[str, Any]:
        """
        Sets the active Google Cloud Project ID and writes it to credentials and environment.
        """
        project_id = project_id.strip()
        if not project_id:
            raise ValueError("Google Cloud Project ID cannot be empty.")

        os.environ["GEOHARVEST_EE_PROJECT"] = project_id
        os.environ["EARTHENGINE_PROJECT"] = project_id
        self._active_project = project_id

        # Update credentials file if it exists
        cred_path = self.credentials_path
        if cred_path.exists():
            try:
                data = json.loads(cred_path.read_text(encoding="utf-8"))
                data["project"] = project_id
                cred_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                cred_path.chmod(0o600)
                logger.info(f"Updated Earth Engine credentials with project: {project_id}")
            except Exception as e:
                logger.warning(f"Could not update project in credentials file: {e}")

        # Update .env file
        try:
            from backend.app.dependencies.config import settings
            env_file = settings.base_dir / ".env"
            if env_file.exists():
                content = env_file.read_text(encoding="utf-8")
                lines = content.splitlines()
                updated = False
                new_lines = []
                for line in lines:
                    if line.startswith("GEOHARVEST_EE_PROJECT="):
                        new_lines.append(f"GEOHARVEST_EE_PROJECT={project_id}")
                        updated = True
                    else:
                        new_lines.append(line)
                if not updated:
                    new_lines.append(f"GEOHARVEST_EE_PROJECT={project_id}")
                env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not update .env with project ID: {e}")

        return self.get_status()

    def authenticate_service_account(
        self,
        service_account_info: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Configures authentication using a Google Cloud Service Account JSON key.
        """
        if not check_ee_available():
            raise RuntimeError("earthengine-api package is not installed.")

        client_email = service_account_info.get("client_email")
        if not client_email:
            raise ValueError("Service account JSON must contain 'client_email'.")

        resolved_project = project_id or service_account_info.get("project_id") or self.get_stored_project_id()

        try:
            from backend.app.dependencies.config import settings
            sa_dir = settings.data_dir / "credentials"
            sa_dir.mkdir(parents=True, exist_ok=True)
            sa_path = sa_dir / "ee_service_account.json"
            sa_path.write_text(json.dumps(service_account_info, indent=2), encoding="utf-8")
            sa_path.chmod(0o600)

            try:
                from google.oauth2 import service_account
                scopes = getattr(ee.oauth, "SCOPES", [
                    "https://www.googleapis.com/auth/earthengine",
                    "https://www.googleapis.com/auth/cloud-platform",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/devstorage.full_control"
                ])
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info,
                    scopes=scopes
                )
            except Exception:
                credentials = ee.ServiceAccountCredentials(client_email, str(sa_path))

            ee.Initialize(credentials, project=resolved_project)
            self._is_initialized = True
            if resolved_project:
                self.set_project_id(resolved_project)

            logger.info(f"Initialized Earth Engine with service account: {client_email}")
            return {
                "success": True,
                "message": f"Successfully initialized with service account {client_email}",
                "status": self.get_status()
            }
        except Exception as e:
            logger.error(f"Service account authentication failed: {e}", exc_info=True)
            raise RuntimeError(f"Service account initialization failed: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """
        Inspects the current Earth Engine authentication state.
        Verifies credentials and tests active initialization.
        """
        if not check_ee_available():
            return {
                "available": False,
                "is_authenticated": False,
                "initialized": False,
                "project_id": None,
                "credentials_exist": False,
                "credentials_path": str(self.credentials_path),
                "error": "earthengine-api is not installed.",
                "message": "Earth Engine Python library missing.",
            }

        cred_path = self.credentials_path
        credentials_exist = cred_path.exists()
        stored_project = self.get_stored_project_id()
        has_refresh_token = False
        scopes = []

        if credentials_exist:
            try:
                data = json.loads(cred_path.read_text(encoding="utf-8"))
                has_refresh_token = bool(data.get("refresh_token"))
                scopes = data.get("scopes", [])
                if not stored_project and data.get("project"):
                    stored_project = str(data.get("project")).strip()
            except Exception as e:
                logger.warning(f"Failed to parse credentials file: {e}")

        # Attempt ee.Initialize()
        init_success = False
        init_error = None
        try:
            if stored_project:
                ee.Initialize(project=stored_project)
                init_success = True
                self._is_initialized = True
            else:
                # If credentials exist, try without project to see what error or if legacy
                ee.Initialize()
                init_success = True
                self._is_initialized = True
        except Exception as e:
            init_error = str(e)
            self._is_initialized = False

        is_authenticated = credentials_exist and has_refresh_token
        status_message = "Ready" if init_success else (
            "Cloud Project ID required" if is_authenticated and not stored_project else
            (init_error or "Not authenticated")
        )

        return {
            "available": True,
            "is_authenticated": is_authenticated or init_success,
            "initialized": init_success,
            "project_id": stored_project,
            "credentials_exist": credentials_exist,
            "credentials_path": str(cred_path),
            "scopes": scopes,
            "auth_page_url": "https://code.earthengine.google.com/client-auth",
            "error": init_error if not init_success else None,
            "message": status_message,
        }

    def logout(self) -> Dict[str, Any]:
        """Clears or backs up the current Earth Engine credentials."""
        cred_path = self.credentials_path
        if cred_path.exists():
            try:
                backup = cred_path.with_suffix(".json.bak")
                cred_path.rename(backup)
                logger.info(f"Backed up credentials to {backup}")
            except Exception as e:
                logger.warning(f"Failed to clear credentials file: {e}")

        self._is_initialized = False
        self._active_project = None
        if "GEOHARVEST_EE_PROJECT" in os.environ:
            del os.environ["GEOHARVEST_EE_PROJECT"]

        return self.get_status()


ee_auth_manager = EarthEngineAuthManager()
