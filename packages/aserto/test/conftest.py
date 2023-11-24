import os.path
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import grpc
import pytest
import requests


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
    directory_gw: Service

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
            f"topaz import -i -d {path}",
            shell=True,
            capture_output=True,
            check=True,
        )

    def set_manifest(self, manifest_path: str) -> None:
        with open(manifest_path, "r") as f:
            manifest = f.read()
        resp = requests.post(
            f"https://{self.directory_gw.address}/api/v3/directory/manifest",
            data=manifest,
            verify=self.directory_gw.ca_cert_path,
        )
        resp.raise_for_status()

    def wait_for_ready(self) -> None:
        t0 = datetime.now()
        while not os.path.exists(self.directory_grpc.ca_cert_path):
            if t0 + timedelta(minutes=1) > datetime.now():
                raise TimeoutError
            time.sleep(1)
        channel = connect(self.directory_grpc)
        grpc.channel_ready_future(channel).result()


@pytest.fixture(scope="module")
def topaz():
    Topaz.stop()

    topaz_db_dir = os.path.expanduser("~/.config/topaz/db")

    if os.path.exists(f"{topaz_db_dir}/directory.db"):
        os.rename(f"{topaz_db_dir}/directory.db", f"{topaz_db_dir}/directory.bak")

    svc = topaz_configure()
    svc.start()
    svc.wait_for_ready()

    svc.set_manifest("test/assets/manifest.yaml")
    svc.import_data("test/assets")

    yield svc

    svc.stop()

    subprocess.run(
        "rm ~/.config/topaz/db/directory.db",
        shell=True,
        capture_output=True,
        check=True,
    )

    if os.path.exists(f"{topaz_db_dir}/directory.bak"):
        os.rename(f"{topaz_db_dir}/directory.bak", f"{topaz_db_dir}/directory.db")


def topaz_configure() -> Topaz:
    subprocess.run(
        "topaz configure -r ghcr.io/aserto-policies/policy-todo:2.1.0 -n todo -d",
        shell=True,
        capture_output=True,
        check=True,
    )

    ca_cert_path_grpc = os.path.expanduser("~/.config/topaz/certs/grpc-ca.crt")
    ca_cert_path_gw = os.path.expanduser("~/.config/topaz/certs/gateway-ca.crt")

    return Topaz(
        authorizer=Service("localhost:8282", ca_cert_path=ca_cert_path_grpc),
        directory_grpc=Service("localhost:9292", ca_cert_path=ca_cert_path_grpc),
        directory_gw=Service("localhost:9393", ca_cert_path=ca_cert_path_gw),
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
