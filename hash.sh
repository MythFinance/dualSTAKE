#!/usr/bin/env bash

set -eo pipefail

cd artifacts

mkdir -p hashes

for filename in *.tok *.tok.page?; do
  hash=$(openssl dgst -sha512-256 $filename | awk '{print $2}')
  dest="hashes/$filename.sha512-256"
  echo -n "$hash" > $dest
  echo "File $filename SHA512/256 $hash written to $dest"
done
