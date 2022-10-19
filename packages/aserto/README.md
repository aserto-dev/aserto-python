# Aserto API client
High-level client interface to Aserto's APIs.

At the moment this only supports interacting with Aserto's [Authorizer service](https://docs.aserto.com/docs/authorizer-guide/overview).
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
from aserto.client import AuthorizerOptions, Identity
from aserto.client.api.authorizer import AuthorizerClient


client = AuthorizerClient(
    identity=Identity(type="NONE"),
    options=AuthorizerOptions(
        api_key=ASERTO_API_KEY,
        tenant_id=ASERTO_TENANT_ID,
        service_type="gRPC",
    ),
)

result = await client.decision_tree(
    decisions=["visible", "enabled", "allowed"],
    policy_name=ASERTO_POLICY_NAME,
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
