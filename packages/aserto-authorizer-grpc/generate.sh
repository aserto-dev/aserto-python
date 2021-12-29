# Prerequisites to running this script:
# - Have Python 3.7 installed and on your path. Must be exactly 3.7, not older or newer.
#   - Have the Python dev dependencies defined in pyproject.yaml installed
#   - Highly recommend using virtualenv to ensure that the `python` points to python3.7 
#     and running this script from within the virtualenv.
# - Have Go installed and on your path
#   - Have Go dependencies installed
# - Have Buf credentials in your ~/.netrc file

# Stop running the script when any error is encountered
set -e

### Generation step ###

# Add current Python virtualenv bin to PATH so buf
# can see the Python betterproto plugin for protoc
PATH="$PATH:$(poetry env info --path)/bin" go run mage.go generate

### Vendoring step ###
# We're vendoring python-betterproto because the latest version (v2.0.0b3)
# will start breaking in Python 3.10 and also there's a mypy typing bug.
# Both of these issue have been fixed in https://github.com/danielgtaylor/python-betterproto/pull/264
# but they still need to release a new version with the fix.

echo 'Vendoring python-betterproto'

# Remove local clone of python-betterproto if it exists
yes | rm -r python-betterproto 2> /dev/null || true

git clone \
  https://github.com/danielgtaylor/python-betterproto 2> /dev/null
cd python-betterproto
# Checkout the revision with the fix mentioned above
git checkout c424b6f 2> /dev/null
cd ..

rm -r src/_asertoproto 2> /dev/null || true
mv python-betterproto/src/betterproto src/_asertoproto
# Also move the README which contains python-betterproto's license
mv python-betterproto/README.md src/_asertoproto//README.md

# Remove unneeded line that breaks things
grep -v __version__ src/_asertoproto/__init__.py > src/_asertoproto/__temp__
mv src/_asertoproto/__temp__ src/_asertoproto/__init__.py

# Remove some unneeded files
rm -r src/_asertoproto/{compile,plugin,templates,_version.py}
rm -r src/_asertoproto/lib/google/protobuf/compiler

# Cleanup
echo 'Cleaning up...'

yes | rm -r python-betterproto

# Avoid import conflict if user already has betterproto installed
# by renaming the package from betterproto to asertoproto
cd src
grep -rl betterproto . | LC_ALL=C xargs sed -i "" -e 's/betterproto/_asertoproto/g'

cd aserto_authorizer_grpc
# Re-export this module for the public package interface
grep -rl 'as _asertoproto_lib_google_protobuf' . \
    | LC_ALL=C xargs sed -i "" -e 's/as _asertoproto_lib_google_protobuf/as _asertoproto_lib_google_protobuf; Proto = _asertoproto_lib_google_protobuf/g'

echo 'Done'