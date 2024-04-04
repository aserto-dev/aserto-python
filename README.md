# Aserto API client

High-level client interface to Aserto's APIs.

## Authorizer
The client can be used for interacting with Aserto's [Authorizer service](https://docs.aserto.com/docs/authorizer-guide/overview).

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
from aserto.client.authorizer import AuthorizerClient


client = AuthorizerClient(
    identity=Identity(type="NONE"),
    options=AuthorizerOptions(
        api_key=ASERTO_API_KEY,
        tenant_id=ASERTO_TENANT_ID,
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

The Directory APIs can be used to interact with the aserto directory services.
It provides CRUD operations on objects and relations, including bulk import and export.
The client can also be used to check whether a user has a permission or relation on an object instance.

### Directory Client

You can initialize a directory client as follows:

```py
from aserto.client.directory.v3 import Directory

ds = Directory(api_key="my_api_key", tenant_id="1234", address="localhost:9292")
```

- `address`: hostname:port of directory service (_required_)
- `api_key`: API key for directory service (_required_ if using hosted directory)
- `tenant_id`: Aserto tenant ID (_required_ if using hosted directory)
- `cert`: Path to the grpc service certificate when connecting to local topaz instance.

#### `get_object`

Get a directory object instance with the type and the id, optionally with the object's relations.

```py
# without relations:
user = ds.get_object(object_type="user", object_id="euang@acmecorp.com")

# with relations:
page = PaginationRequest(size=10)
while True:
    resp = ds.get_object(object_type="user", object_id="euang@acmecorp.com", with_relations=True, page=page)
    user = resp.result               # The returned object.
    relations_page = resp.relations  # A page of relations.

    if not resp.page.next_token:
        # we've reached the last page.
        break

    # request the next page.
    page.token = resp.page.next_token

```

#### `get_objects_many`

Similar to `get_object` but can retrieve multiple object instances in a single request.
```py
objects = ds.get_object_many(
    [
        ObjectIdentifier(type="user", id="euan@acmecorp.com"),
        ObjectIdentifier(type="group", id="marketing"),
    ]
)
```

#### `get_objects`

Get object instances with an object type type pagination info (page size and pagination token).

```py
from aserto.client.directory.v3 import PaginationRequest

users = ds.get_objects(object_type="user", page=PaginationRequest(size=10))
```


#### `set_object`

Create an object instance with the specified properties. If an `etag` is specified and is different from the current
object's etag, the call raises an `ETagMismatchError`.

```py
# pass object fields as arguments:
user = ds.set_object(
    object_type="user",
    object_id="new-user@acmecorp.com",
    display_name="John Doe",
    "properties": {"active": True, "department": "Engineering"},
}

# set_object can also take an Object parameter:
user.display_name = "Jane Doe"
user.properties["title"] = "Senior Engineer"
updated_user = ds.set_object(object=user)
```

#### `delete_object`

Delete an object instance and optionally its relations, using its type and id:

```py
# delete an object
ds.delete_object(object_type="user", object_id="test-object")

# delete an object and all its relations
ds.delete_object(object_type="user", object_id="test-object", with_relations=True)
```

#### `get_relation`

Retrieve a single relation from the directory or raise a `NotFoundError` if no matching relation exists.

```py
# get the manager of euang@acmecorp.com:
relation = ds.get_relation(
    object_type="user",
    relation="manager",
    subject_type="user",
    subject_id="euang@acmecorp.com",
)

assert relation.object_id

# include the relation's object and subject in the response:
response = ds.get_relation(
    object_type="user",
    relation="manager",
    subject_type="user",
    subject_id="euang@acmecorp.com",
    with_relations=True,
)

assert response.relation.object_id
assert response.subject.display_name == "Euan Garden"
assert response.object.properties["department"] == "Sales"
#
```

#### `get_relations`

Searches the directory for relations matching the specified criteria, optionally including the object and subject
of each returned relation.

```py
# find all groups a user is a member of:
page = PaginationRequest(size=10)

while True:
    response = ds.get_relations(
        object_type="group",
        "relation"="member",
        "subject_type": "user",
        "subject_id": "euang@acmecorp.com",
        with_objects=True,
        page=page,
    )

    if not response.page.next_token:
        break

    page.token = response.page.next_token
```

#### `set_relation`

Create a new relation.

```py
ds.set_relation(
    object_type="group",
    object_id="admin",
    relation="member",
    subject_type="user",
    subject_id="euang@acmecorp.com",
)
```

#### `delete_relation`

Delete a relation.

```py
ds.delete_relation(
    object_type="group",
    object_id="admin",
    relation="member",
    subject_type="user",
    subject_id="euang@acmecorp.com",
)
```

#### `check`

Check if a subject has a given relation or permission on an object.

```py
allowed = ds.check(
    object_type="folder",
    object_id="/path/to/folder",
    relation="can_delete",
    subject_type="user",
    subject_id="euang@acmecorp.com",
)
```

#### `find_subjects`

Find subjects that have a given relation to or permission on a specified object.

```py
reponse = ds.find_subjects(
    object_type="folder",
    object_id="/path/to/folder",
    relation="can_delete",
    subject_type="user"
)

assert ObjectIdentifier("user", "euang@acmecorp.com") in response.results
```

#### `find_objects`

Find objects that a given subject has a specified relation to or permission on.

```py
reponse = ds.find_objects(
    object_type="folder",
    relation="can_delete",
    subject_type="user"
    subjecct_id="euang@acmecorp.com"
)

assert ObjectIdentifier("folder", "/path/to/folder") in response.results
```

#### `get_manifest `

Download the directory manifest.

```py
manifest = ds.get_manifest()

print(manifest.body)    # yaml manifest

# conditionally get the manifest if its etag has changed
new_manifest = ds.get_manifest(etag=manifest.etag)

assert new_manifest is None   # the manifest hasn't changed
```

#### `set_manifest`

Upload a new directory manifest.

```py
with open("manifest.yaml", "rb") as f:
    manifest = f.read()

ds.set_manifest(manifest)
```

#### `import_data`

Bulk-insert objects and/or relations to the directory. Returns a summary of the number of objects/relations affected.

```py
# import an object and a relation.
data = [
    Object(type="user", id="test@acmecorp.com"),
    Relation(
        object_type="user",
        object_id="euang@acmecorp.com",
        relation="manager",
        subject_type="user",
        subject_id="test@acmecorp.com",
    ),
]

response = ds.import_data(data)

assert response.objects.set == 1
assert response.object.error == 0
assert response.relations.set == 1
assert response.relations.error == 0
```

#### `export_data`

Bulk-retrieve objects and/or relations from the directory.


```py
from aserto.client.directory.v3 import ExportOption, Object, Relation

# export all objects and relations
for item in ds.export(ExportOption.OPTION_DATA):
    if isinstance(item, Object):
        print("object:", item)
    elif isinstance(item, Relation):
        print("relation:", item)
```

### Async Directory Client

You can initialize an asynchronous directory client as follows:

```py
from aserto.client.directory.v3.aio import Directory

ds = Directory(api_key="my_api_key", tenant_id="1234", address="localhost:9292")
```

The methods on the async directory have the same signatures as their synchronous counterparts.

### Directory v2 client

To interact with older instances of the directory service, a v2 client is available with limited functionality.
The v2 client doesn't support `get_manifest`/`set_manifest`, and `import_data`/`export_data`.

```py
from aserto.client.directory.v2 import Directory
ds = Directory(api_key="my_api_key", tenant_id="1234", address="localhost:9292")
```

## License

This project is licensed under the MIT license. See the [LICENSE](https://github.com/aserto-dev/aserto-python/blob/main/LICENSE) file for more info.
