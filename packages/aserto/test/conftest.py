import os.path
import subprocess
import uuid
from dataclasses import dataclass
from typing import Optional

import grpc
import pytest

from aserto.client.directory import Directory, Object


@dataclass(frozen=True)
class Service:
    address: str
    api_key: Optional[str] = None
    tenant_id: Optional[str] = None
    ca_cert_path: Optional[str] = None


@dataclass(frozen=True)
class Topaz:
    authorizer: Service
    directory: Service


@pytest.fixture(scope="package")
def topaz():
    svc = topaz_configure()
    topaz_start()
    topaz_wait_for_ready(svc.authorizer)
    yield svc
    topaz_stop()


def topaz_configure() -> Topaz:
    subprocess.run(
        "topaz configure -r ghcr.io/aserto-policies/policy-todo:2.1.0 -n todo -d -s",
        shell=True,
        capture_output=True,
        check=True,
    )

    ca_cert_path = os.path.expanduser("~/.config/topaz/certs/grpc-ca.crt")

    return Topaz(
        authorizer=Service("localhost:8282", ca_cert_path=ca_cert_path),
        directory=Service("localhost:9292", ca_cert_path=ca_cert_path),
    )


def topaz_start() -> None:
    subprocess.run(
        "topaz start",
        shell=True,
        capture_output=True,
        check=True,
    )


def topaz_stop() -> None:
    subprocess.run(
        "topaz stop",
        shell=True,
        capture_output=True,
        check=True,
    )


def topaz_wait_for_ready(svc: Service) -> None:
    channel = connect(svc)
    grpc.channel_ready_future(channel).result()


def connect(svc: Service) -> grpc.Channel:
    return grpc.secure_channel(
        target=svc.address, credentials=grpc.ssl_channel_credentials(read_cert(svc.ca_cert_path))
    )


def read_cert(path: Optional[str]) -> Optional[bytes]:
    if path is None:
        return None

    with open(path, "rb") as f:
        return f.read()


@pytest.fixture
def directory_client(topaz):
    directory = Directory.connect(
        address=topaz.directory.address, ca_cert=topaz.directory.ca_cert_path
    )

    yield directory


@pytest.fixture
def directory_setup(topaz, directory_client):
    directory = directory_client

    key_1 = uuid.uuid4().hex
    key_2 = uuid.uuid4().hex

    obj_1 = directory.set_object(Object(key=key_1, type="user", display_name="test user"))
    obj_2 = directory.set_object(Object(key=key_2, type="group", display_name="test group"))

    relation = directory.set_relation(
        relation={
            "subject": {"key": obj_1.key, "type": obj_1.type},
            "object": {"key": obj_2.key, "type": obj_2.type},
            "relation": "member",
        }
    )

    yield obj_1, obj_2, relation
