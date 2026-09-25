"""Authenticate the MLflow Python client through Cloudflare Access (Zero Trust).

`mlflow.caabi.dev` sits behind a Cloudflare Tunnel with an Access policy. Browsers log in
interactively; machines present a *service token* as two request headers:

    CF-Access-Client-Id:     <client_id>.access
    CF-Access-Client-Secret: <client_secret>

MLflow has no environment variable for arbitrary headers, but every REST call it makes —
tracking, model registry and proxied artifact transfer — merges headers from all registered
`RequestHeaderProvider`s. This module provides one, driven by two environment variables.

It is registered two ways for robustness:
  * declaratively, via the `mlflow.request_header_provider` entry point in pyproject.toml
    (active whenever the package is pip-installed — the Docker image, CI, the workstation);
  * programmatically, by `configure()`, for a bare `python -m ...` checkout.

When both variables are unset the provider stays dormant, so the same code talks to
`http://mlflow:5000` on the Droplet's Docker network without any Cloudflare hop.
"""

from __future__ import annotations

import logging
import os

import mlflow
from mlflow import MlflowClient
from mlflow.tracking.request_header.abstract_request_header_provider import RequestHeaderProvider

log = logging.getLogger(__name__)

CF_ID_ENV = "CF_ACCESS_CLIENT_ID"
CF_SECRET_ENV = "CF_ACCESS_CLIENT_SECRET"  # noqa: S105  # nosec B105 — the variable *name*, not a secret


class CloudflareAccessHeaderProvider(RequestHeaderProvider):
    """Adds Cloudflare Access service-token headers to every MLflow HTTP request."""

    def in_context(self) -> bool:
        return bool(os.getenv(CF_ID_ENV) and os.getenv(CF_SECRET_ENV))

    def request_headers(self) -> dict[str, str]:
        return {
            "CF-Access-Client-Id": os.environ[CF_ID_ENV],
            "CF-Access-Client-Secret": os.environ[CF_SECRET_ENV],
        }


def ensure_registered() -> None:
    """Idempotently register the provider (no-op if the entry point already did it)."""
    from mlflow.tracking.request_header.registry import _request_header_provider_registry as registry

    if not any(isinstance(p, CloudflareAccessHeaderProvider) for p in registry):
        registry.register(CloudflareAccessHeaderProvider)


def configure(tracking_uri: str, client_id: str | None = None, client_secret: str | None = None) -> None:
    """Point MLflow at the tracking server and arm the service-token provider.

    Values passed explicitly (e.g. from pydantic-settings / a .env file) are exported to the
    process environment because MLflow instantiates header providers itself.
    """
    if client_id and client_secret:
        os.environ[CF_ID_ENV] = client_id
        os.environ[CF_SECRET_ENV] = client_secret
    ensure_registered()
    mlflow.set_tracking_uri(tracking_uri)
    log.info(
        "mlflow configured",
        extra={"tracking_uri": tracking_uri, "cf_access": CloudflareAccessHeaderProvider().in_context()},
    )


def verify_connection() -> str:
    """Round-trip to the tracking server and translate the classic Cloudflare failure mode.

    If the token is missing or not allowed by the Access policy, Cloudflare answers with its
    HTML login page instead of JSON and MLflow raises a decode error.
    """
    try:
        MlflowClient().search_experiments(max_results=1)
    except Exception as exc:
        text = str(exc)
        if "Expecting value" in text or "<html" in text.lower() or "302" in text:
            raise RuntimeError(
                "MLflow returned a non-JSON response — almost certainly the Cloudflare Access login "
                "page. Check CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET and that the Access "
                "application for mlflow.caabi.dev has a *Service Auth* policy including this token."
            ) from exc
        raise
    return mlflow.get_tracking_uri()
