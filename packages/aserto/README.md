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
    policy_instance_name=ASERTO_POLICY_INSTANCE_NAME,
    policy_instance_label=ASERTO_POLICY_INSTANCE_LABEL,
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

## Directory

The Directory APIs can be used to get or set object instances and relation instances. They can also be used to check whether a user has a permission or relation on an object instance.

### Directory Client

You can initialize a directory client as follows:

```py
from aserto.client.directory import Directory

ds = Directory(api_key="my_api_key", tenant_id="1234", address="localhost:9292")
```

- `address`: hostname:port of directory service (_required_)
- `api_key`: API key for directory service (_required_ if using hosted directory)
- `tenant_id`: Aserto tenant ID (_required_ if using hosted directory)
- `cert`: Path to the grpc service certificate when connecting to local topaz instance.

#### 'get_object' function

Get a directory object instance with the type and the key.

```py
user = ds.get_object(type="user", key="euang@acmecorp.com")
```

#### 'get_objects' function

Get object instances with an object type type and page size.

```py
from aserto.client.directory import PaginationRequest

users = ds.get_objects(object_type="user", page=PaginationRequest(size=10))
```

#### 'set_object' function

Create an object instance with the specified fields. For example:

```py
from google.protobuf.json_format import ParseDict
from google.protobuf.struct_pb2 import Struct

properties = ParseDict({"displayName": "test object"}, Struct())

user = ds.set_object(object={
    "type": "user",
    "key": "test-object",
    "properties": properties,
})
```

#### 'delete_object' function

Delete an object instance using its type and key:

```py
ds.delete_object(type="user", key="test-object")
```

### Async Directory Client

You can initialize an asynchronous directory client as follows:

```py
from aserto.client.directory.aio import Directory

ds = Directory(api_key="my_api_key", tenant_id="1234", address="localhost:9292")
```

#### async 'set_relation' function

Create a new relation with the specified fields. For example:

```py
relation = await ds.set_relation(
    relation={
        "subject": {"key": "test-subject", "type": "user"},
        "object": {"key": "test-object", "type": "group"},
        "relation": "member",
    }
)
```

## License

This project is licensed under the MIT license. See the [LICENSE](https://github.com/aserto-dev/aserto-python/blob/main/LICENSE) file for more info.
