# Aserto - Welcome to modern authorization
This is the home of all the packages that will allow you to use [Aserto](https://www.aserto.com/)'s services from your Python code.
## Packages
[`aserto`](https://github.com/aserto-dev/aserto-python/tree/main/packages/aserto) - Provides a high level interface to Aserto's services. It's the recommended package to fall back to when the web framework integrations don't fit your needs. 

[`aserto-authorizer-grpc`](https://github.com/aserto-dev/aserto-python/tree/main/packages/aserto-authorizer-grpc) - Lower-level interface specifically to Aserto's Authorizer service. This is for advanced users that need more fine-grained control than the `aserto` package provides.

[`aserto-idp`](https://github.com/aserto-dev/aserto-python/tree/main/packages/aserto-idp) - Used to more easily create identity providers for Aserto's other packages.
### Web framework integration
[`flask-aserto`](https://github.com/aserto-dev/aserto-python/tree/main/packages/flask-aserto) - For easier integration into [Flask](https://github.com/pallets/flask) apps.

...more on the way!