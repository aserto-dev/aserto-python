# Aserto API client
High-level client interface to Aserto's APIs.

At the moment this only supports interacting with Aserto's [Authorizer service](https://docs.aserto.com/authorizer-guide/overview).
## Installation
### Using Pip
```sh
pip install aserto
```
### Using Poetry
```sh
poetry add aserto
```
## Usage
```py
from aserto import HostedAuthorizer, Identity
from aserto.api.authorizer import AuthorizerClient


client = AuthorizerClient(
    tenant_id=ASERTO_TENANT_ID,
    identity=Identity(type="NONE"),
    authorizer=HostedAuthorizer(api_key=ASERTO_API_KEY, service_type="gRPC"),
)

result = await client.decision_tree(
    decisions=["visible", "enabled", "allowed"],
    policy_id=ASERTO_POLICY_ID,
    policy_path_root=ASERTO_POLICY_PATH_ROOT,
    policy_path_separator="DOT",
)

assert result == {
    "GET.your.policy.path": {
        "visible": True,
        "enabled": True,
        "allowed": False,
    },
}
```