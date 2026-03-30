"""AWS Cognito authentication for the Heatit cloud API."""

from __future__ import annotations

import asyncio
import os
import time

from .exceptions import HeatitAuthError

# Heatit Cognito configuration (from tf.api.ouman-cloud.com/users/endpoint)
COGNITO_REGION = "eu-west-1"
USER_POOL_ID = "eu-west-1_2lWTXCKVV"
CLIENT_ID = "6spbss1b6lglcco8t3dtiv961e"


def _create_and_authenticate(username: str, password: str) -> tuple:
    """Create Cognito client and authenticate (sync, runs in executor)."""
    # Prevent boto3 from trying to contact EC2 metadata service
    os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
    os.environ.setdefault("AWS_DEFAULT_REGION", COGNITO_REGION)

    import boto3
    from botocore.config import Config
    from pycognito import Cognito

    # Create a boto3 client that won't look for AWS credentials
    client = boto3.client(
        "cognito-idp",
        region_name=COGNITO_REGION,
        config=Config(signature_version=boto3.session.UNSIGNED),
        aws_access_key_id="",
        aws_secret_access_key="",
    )

    cognito = Cognito(
        USER_POOL_ID,
        CLIENT_ID,
        username=username,
        boto3_client=client,
    )
    cognito.authenticate(password=password)
    return cognito.id_token, cognito.access_token, cognito.refresh_token, cognito


def _refresh_tokens(cognito, id_token, access_token, refresh_token) -> tuple:
    """Refresh tokens (sync, runs in executor)."""
    cognito.id_token = id_token
    cognito.access_token = access_token
    cognito.refresh_token = refresh_token
    cognito.renew_access_token()
    return cognito.id_token, cognito.access_token


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
            loop = asyncio.get_running_loop()
            id_token, access_token, refresh_token, cognito = (
                await loop.run_in_executor(
                    None,
                    _create_and_authenticate,
                    self._username,
                    self._password,
                )
            )

            self._cognito = cognito
            self._id_token = id_token
            self._access_token = access_token
            self._refresh_token = refresh_token
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
            if not self._cognito:
                raise HeatitAuthError("No cognito session to refresh")

            loop = asyncio.get_running_loop()
            id_token, access_token = await loop.run_in_executor(
                None,
                _refresh_tokens,
                self._cognito,
                self._id_token,
                self._access_token,
                self._refresh_token,
            )

            self._id_token = id_token
            self._access_token = access_token
            self._token_expiry = time.time() + 3500

            return self._id_token

        except Exception as err:
            self._refresh_token = None
            raise HeatitAuthError(f"Token refresh failed: {err}") from err

    async def close(self) -> None:
        """No resources to release."""
        pass
