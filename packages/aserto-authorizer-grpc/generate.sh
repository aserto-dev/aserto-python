# Prerequisites to running this script:
# - Have Python 3+ installed and on your path
#   - Have the Python dev dependencies defined in pyproject.yaml installed
#   - Highly recommend using virtualenv to ensure that the `python` points to python3.7 
#     and running this script from within the virtualenv.
# - Have Go installed
#   - Have Go dependencies installed
# - Have Mage installed and on your path
# - Have Buf credentials in your ~/.netrc file

# Stop running the script when any error is encountered
set -e

# Add current Python virtualenv bin to PATH so buf
# can see the Python betterproto plugin for protoc
PATH="$PATH:$(poetry env info --path)/bin" mage generate

# Include convenience export so dependents don't need to refer to `betterproto` directly
echo 'import betterproto.lib.google.protobuf as Proto

__all__ = ["Proto"]
' > src/aserto_authorizer_grpc/__init__.py