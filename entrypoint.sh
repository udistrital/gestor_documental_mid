#!/usr/bin/env bash

set -e
set -u
set -o pipefail

if [ -n "${PARAMETER_STORE:-}" ]; then
  export NUXEO_USERNAME="$(aws ssm get-parameter --name /${PARAMETER_STORE}/gestor_documental_mid/nuxeo/username --output text --query Parameter.Value)"
  export NUXEO_PASSWORD="$(aws ssm get-parameter --with-decryption --name /${PARAMETER_STORE}/gestor_documental_mid/nuxeo/password --output text --query Parameter.Value)"
  export ENCRYPTION_KEY="$(aws ssm get-parameter --with-decryption --name /${PARAMETER_STORE}/gestor_documental_mid/nuxeo/encryption_key --output text --query Parameter.Value)"
fi

python api.py