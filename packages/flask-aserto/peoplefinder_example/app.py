from flask import Flask, jsonify, request
from flask.wrappers import Response
from flask_cors import CORS

from flask_aserto import AsertoMiddleware, AuthorizationError

from .aserto_options import load_aserto_options_from_environment
from .people_client import PeopleClient

app = Flask(__name__)

CORS(app, headers=["Content-Type", "Authorization"])

# Check authorization by initializing the Aserto middleware with options
aserto_options = load_aserto_options_from_environment()
aserto = AsertoMiddleware(**aserto_options)

# Set up middleware to return the display state map for this service
aserto.register_display_state_map(app)


# Handle `AuthorizationError`s that may be raised by Aserto
@app.errorhandler(AuthorizationError)  # type: ignore[arg-type]
def handle_auth_error(exception: AuthorizationError) -> Response:
    return Response(response=f"Forbidden by policy {exception.policy_path}", status=403)


# Use `authorize` as middleware in the route dispatch path
@app.route("/api/users/<id>", methods=["GET", "PUT", "POST", "DELETE"])
@aserto.authorize
async def api_user(id: str) -> Response:
    people_client = PeopleClient(
        tenant_id=aserto_options["authorizer"].tenant_id,
        authorizer_api_key=aserto_options["authorizer"].api_key,
        authorizer_url=aserto_options["authorizer"].url,
    )

    if request.method == "GET":
        response = jsonify(await people_client.get_person(id))
    elif request.method == "PUT" or request.method == "POST":
        response = jsonify(
            await people_client.update_person(id, request.get_json(silent=True)),
        )
        response.status_code = 201
    else:
        response = jsonify({"message": "Not implemented"})
        response.status_code = 501

    return response


# Instead of `authorize`, use the `check` function
# for a more imperative style of authorization
@app.route("/api/users", methods=["GET"])
async def api_users() -> Response:
    if not await aserto.check("allowed"):
        return Response(status=403)

    people_client = PeopleClient(
        tenant_id=aserto_options["authorizer"].tenant_id,
        authorizer_api_key=aserto_options["authorizer"].api_key,
        authorizer_url=aserto_options["authorizer"].url,
    )

    return jsonify(await people_client.list_people())
