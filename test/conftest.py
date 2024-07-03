from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os.path
import subprocess
import time
from typing import Optional

import grpc
import pytest


@dataclass(frozen=True)
class Service:
    address: str
    api_key: str = ""
    tenant_id: str = ""
    ca_cert_path: str = ""


@dataclass(frozen=True)
class Topaz:
    authorizer: Service
    directory_grpc: Service

    @staticmethod
    def start() -> None:
        subprocess.run(
            "topaz start",
            shell=True,
            capture_output=True,
            check=True,
        )

    @staticmethod
    def stop() -> None:
        subprocess.run(
            "topaz stop",
            shell=True,
            capture_output=True,
            check=True,
        )

    @staticmethod
    def import_data(path: str) -> None:
        subprocess.run(
            f"topaz ds import -i -d {path}",
            shell=True,
            capture_output=True,
            check=True,
        )

    @staticmethod
    def set_manifest(manifest_path: str) -> None:
        subprocess.run(
            f"topaz ds delete manifest --force -i",
            shell=True,
            capture_output=True,
            check=True,
        )

        subprocess.run(
            f"topaz ds set manifest {manifest_path} -i",
            shell=True,
            capture_output=True,
            check=True,
        )

    def wait_for_ready(self) -> None:
        t0 = datetime.now()
        while not os.path.exists(self.directory_grpc.ca_cert_path):
            if t0 + timedelta(minutes=2) < datetime.now():
                raise TimeoutError
            time.sleep(1)
        channel = connect(self.directory_grpc)
        grpc.channel_ready_future(channel).result()


@pytest.fixture(scope="module")
def topaz():
    Topaz.stop()

    svc = topaz_configure()
    svc.start()
    svc.wait_for_ready()

    svc.set_manifest("test/assets/manifest.yaml")
    svc.import_data("test/assets")

    yield svc

    svc.stop()

    time.sleep(1)


def topaz_configure() -> Topaz:
    subprocess.run(
        "topaz config new -r ghcr.io/aserto-policies/policy-todo:3 -n todo -d -f",
        shell=True,
        capture_output=True,
        check=True,
    )

    subprocess.run(
        "topaz config use todo",
        shell=True,
        capture_output=True,
        check=True,
    )

    config = json.loads(
        subprocess.run(
            "topaz config info",
            shell=True,
            capture_output=True,
            check=True,
        )
        .stdout.decode()
        .strip()
    )

    cert_path = config["config"]["topaz_certs_dir"]
    ca_cert_path_grpc = os.path.join(cert_path, "grpc-ca.crt")

    return Topaz(
        authorizer=Service(
            config["authorizer"]["topaz_authorizer_svc"], ca_cert_path=ca_cert_path_grpc
        ),
        directory_grpc=Service(
            config["directory"]["topaz_directory_svc"], ca_cert_path=ca_cert_path_grpc
        ),
    )


def connect(svc: Service) -> grpc.Channel:
    return grpc.secure_channel(
        target=svc.address, credentials=grpc.ssl_channel_credentials(read_cert(svc.ca_cert_path))
    )


def read_cert(path: Optional[str]) -> Optional[bytes]:
    if path is None:
        return None

    with open(path, "rb") as f:
        return f.read()
