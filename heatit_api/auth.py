"""AWS Cognito authentication for the Heatit cloud API."""

from __future__ import annotations

import asyncio
import time

from .exceptions import HeatitAuthError

# Heatit Cognito configuration (from tf.api.ouman-cloud.com/users/endpoint)
COGNITO_REGION = "eu-west-1"
USER_POOL_ID = "eu-west-1_2lWTXCKVV"
CLIENT_ID = "6spbss1b6lglcco8t3dtiv961e"


class CognitoAuth:
    """Handles AWS Cognito SRP authentication via pycognito."""

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._id_token: str | None = None
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: float = 0
        self._cognito = None

    @property
    def id_token(self) -> str | None:
        return self._id_token

    @property
    def is_expired(self) -> bool:
        return time.time() >= self._token_expiry

    def _get_cognito(self):
        if self._cognito is None:
            from pycognito import Cognito

            self._cognito = Cognito(
                USER_POOL_ID, CLIENT_ID, username=self._username
            )
        return self._cognito

    async def authenticate(self) -> str:
        """Authenticate and return the ID token."""
        if self._id_token and not self.is_expired:
            return self._id_token

        if self._refresh_token and self.is_expired:
            try:
                return await self._refresh()
            except HeatitAuthError:
                pass  # Fall through to full auth

        return await self._initiate_auth()

    async def _initiate_auth(self) -> str:
        """Perform SRP authentication flow."""
        try:
            cognito = self._get_cognito()
            # pycognito is sync, run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, cognito.authenticate, self._password
            )

            self._id_token = cognito.id_token
            self._access_token = cognito.access_token
            self._refresh_token = cognito.refresh_token
            # Cognito tokens expire in 1 hour
            self._token_expiry = time.time() + 3500  # ~58 min buffer

            if not self._id_token:
                raise HeatitAuthError("No ID token received")

            return self._id_token

        except HeatitAuthError:
            raise
        except Exception as err:
            raise HeatitAuthError(f"Authentication failed: {err}") from err

    async def _refresh(self) -> str:
        """Refresh tokens using the refresh token."""
        try:
            cognito = self._get_cognito()
            cognito.id_token = self._id_token
            cognito.access_token = self._access_token
            cognito.refresh_token = self._refresh_token

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, cognito.renew_access_token)

            self._id_token = cognito.id_token
            self._access_token = cognito.access_token
            self._token_expiry = time.time() + 3500

            return self._id_token

        except Exception as err:
            self._refresh_token = None
            raise HeatitAuthError(f"Token refresh failed: {err}") from err

    async def close(self) -> None:
        """No resources to release."""
        pass
