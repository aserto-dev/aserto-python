# Aserto Identity Providers
Common identity providers for use with Aserto client libraries

## Installation
### Using Pip
```sh
pip install aserto-idp
```
### Using Poetry
```sh
poetry add aserto-idp
```
## Current Identity Providers
### Auth0
```py
from aserto_idp.auth0 import generate_oauth_subject_from_auth_header
```
### Stay tuned for more!
## Usage
### With [`aserto-authorizer-grpc`](https://github.com/aserto-dev/aserto-python/tree/HEAD/packages/aserto-authorizer-grpc)
```py
from aserto_authorizer_grpc.aserto.api.v1 import IdentityContext, IdentityType
from aserto_idp.auth0 import AccessTokenError, generate_oauth_subject_from_auth_header


try:
    subject = await generate_oauth_subject_from_auth_header(
        authorization_header=request.headers["Authorization"],
        domain=AUTH0_DOMAIN,
        client_id=AUTH0_CLIENT_ID,
        audience=AUTH0_AUDIENCE,
    )

    identity_context = IdentityContext(
        type=IdentityType.IDENTITY_TYPE_SUB,
        identity=subject,
    )
except AccessTokenError:
    identity_context = IdentityContext(type=IdentityType.IDENTITY_TYPE_NONE)

```
### With [`aserto`](https://github.com/aserto-dev/aserto-python/tree/HEAD/packages/aserto)
```py
from aserto import Identity
from aserto_idp.auth0 import AccessTokenError, generate_oauth_subject_from_auth_header


try:
    subject = await generate_oauth_subject_from_auth_header(
        authorization_header=request.headers["Authorization"],
        domain=AUTH0_DOMAIN,
        client_id=AUTH0_CLIENT_ID,
        audience=AUTH0_AUDIENCE,
    )

    identity = Identity(type="SUBJECT", subject=subject)
except AccessTokenError:
    identity = Identity(type="NONE")
```