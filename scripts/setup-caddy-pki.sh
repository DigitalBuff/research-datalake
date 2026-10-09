#!/usr/bin/env bash
# Generates the static Caddy root CA (once, idempotently) and prints the
# hosts entries needed for trino.datalake.local / auth.datalake.local /
# trino-gateway.datalake.local. The gateway's own leaf certificate is issued
# from this root CA by the `gateway-certs` service in docker-compose.yml.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKI_DIR="${ROOT_DIR}/caddy/pki"
ROOT_CERT="${PKI_DIR}/root.pem"
ROOT_KEY="${PKI_DIR}/root.key"

mkdir -p "${PKI_DIR}"

if [[ -f "${ROOT_CERT}" && -f "${ROOT_KEY}" ]]; then
	echo "Root CA already present at ${PKI_DIR} — leaving it untouched."
else
	echo "Generating static root CA into ${PKI_DIR} ..."
	openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 -nodes \
		-keyout "${ROOT_KEY}" \
		-out "${ROOT_CERT}" \
		-subj "/CN=Datalake PoC Local Root CA" \
		-addext "basicConstraints=critical,CA:TRUE" \
		-addext "keyUsage=critical,keyCertSign,cRLSign"
	chmod 600 "${ROOT_KEY}"
	echo "Root CA generated. Import ${ROOT_CERT} into the Windows VM Trusted Root store and the macOS keychain (one-time-ever)."
fi

echo
echo "=== hosts entries ==="


PARALLELS_HOST_IP="10.211.55.2"

echo "Windows VM (C:\\Windows\\System32\\drivers\\etc\\hosts):"
echo "  ${PARALLELS_HOST_IP} trino.datalake.local auth.datalake.local trino-gateway.datalake.local"
echo
echo "macOS (/etc/hosts):"
echo "  127.0.0.1 trino.datalake.local auth.datalake.local trino-gateway.datalake.local"
