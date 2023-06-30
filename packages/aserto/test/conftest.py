import os.path
import subprocess
from dataclasses import dataclass
from typing import Optional

import grpc
import pytest


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
