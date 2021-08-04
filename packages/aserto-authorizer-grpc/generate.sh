### Generation step ###

# Add current Python virtualenv bin to PATH so buf
# can see the Python betterproto plugin for protoc
PATH="$PATH:$(poetry env info --path)/bin" go run mage.go generate

### Vendoring step ###

# Remove local clone of python-better proto if it exists
yes | rm -r python-betterproto 2> /dev/null || true

git clone \
  https://github.com/danielgtaylor/python-betterproto

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
yes | rm -r python-betterproto

# Avoid import conflict if user already has betterproto installed
# by renaming the package from betterproto to asertoproto
cd src
grep -rl betterproto . | LC_ALL=C xargs sed -i "" -e 's/betterproto/_asertoproto/g'

# Fix a deprecated import that will break in Python v3.10
grep -rl "from collections import AsyncIterable" . \
    | LC_ALL=C xargs sed -i "" -e 's/from collections import AsyncIterable/from collections.abc import AsyncIterable/g'

cd aserto_authorizer_grpc
# Re-export this module for the public package interface
grep -rl 'as _asertoproto_lib_google_protobuf' . \
    | LC_ALL=C xargs sed -i "" -e 's/as _asertoproto_lib_google_protobuf/as _asertoproto_lib_google_protobuf; Proto = _asertoproto_lib_google_protobuf/g'
