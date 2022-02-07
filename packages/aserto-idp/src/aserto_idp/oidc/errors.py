class AccessTokenError(Exception):
    """An error that occurs while processing an access token."""


class DiscoveryError(AccessTokenError):
    """An error that occurs during the OIDC discovery process."""
