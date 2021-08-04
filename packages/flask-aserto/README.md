# Aserto Flask middleware
This is the official library for integrating [Aserto](https://www.aserto.com/) authorization into your [Flask](https://github.com/pallets/flask) applications.

For a example of what this looks like in a running Flask app and guidance on connecting an identity provider, see the [PeopleFinder app example](https://github.com/aserto-dev/aserto-python/tree/main/packages/flask-aserto/peoplefinder_example).

## Features
### Add authorization checks to your routes
```py
from flask_aserto import AsertoMiddleware, AuthorizationError


app = Flask(__name__)
aserto = AsertoMiddleware(**aserto_options)


@app.route("/api/users/<id>", methods=["GET"])
@aserto.authorize
def api_user(id: str) -> Response:
    # Raises an AuthorizationError if the `GET.api.users.__id`
    # policy returns a decision of "allowed = false" 
    ...
```
### Automatically create a route to serve a [Display State Map](https://docs.aserto.com/authorizer-guide/display-state-map)
```py
# Defaults to creating a route at the path "/__displaystatemap" 
aserto.register_display_state_map(app)
```
### Perform more finely controlled authorization checks
```py
@app.route("/api/users/<id>", methods=["GET"])
async def api_user(id: str) -> Response:
    # This also automatically knows to check the `GET.api.users.__id` policy
    if not await aserto.check("allowed"):
        raise AuthorizationError()

    ...
```
