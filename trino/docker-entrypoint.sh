#!/bin/bash
# Generates the file-based password authenticator's password.db from
# TRINO_USER / TRINO_PASSWORD env vars, then starts Trino.
set -euo pipefail

PASSWORD_DB=/data/trino/password.db

: "${TRINO_USER:?TRINO_USER must be set}"
: "${TRINO_PASSWORD:?TRINO_PASSWORD must be set}"

htpasswd -B -C 10 -b -c "${PASSWORD_DB}" "${TRINO_USER}" "${TRINO_PASSWORD}"

exec /opt/trino/bin/launcher run
