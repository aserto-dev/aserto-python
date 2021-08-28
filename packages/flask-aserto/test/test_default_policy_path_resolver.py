from flask import Flask

from flask_aserto._defaults import (
    create_default_policy_path_resolver,
    policy_path_heuristic,
)


def test_heuristic() -> None:
    assert policy_path_heuristic("/api/users") == ".api.users", "Slashes become dots"
    assert policy_path_heuristic("/Upercase") == ".upercase", "Uppercase to lowercase"
    assert policy_path_heuristic("/dotted.route") == ".dotted.route", "Dots stay dots"
    assert (
        policy_path_heuristic("/api/users/<id>") == ".api.users.__id"
    ), "Parameters prefixed with double underscores"


def test_policy_route_concatenation() -> None:
    resolver = create_default_policy_path_resolver("peoplefinder")

    app = Flask(__name__)

    @app.route("/api/users", methods=["GET", "POST"])
    def api_users() -> None:
        return None

    with app.test_client() as client:
        client.get("/api/users")
        assert resolver() == "peoplefinder.GET.api.users"

    with app.test_client() as client:
        client.post("/api/users")
        assert resolver() == "peoplefinder.POST.api.users"
