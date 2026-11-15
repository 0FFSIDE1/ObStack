#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

readonly PKI_DIR="/etc/obstack/pki"
readonly CERT="${PKI_DIR}/central.crt"
readonly KEY="${PKI_DIR}/central.key"
readonly CA_CERT="${PKI_DIR}/ca.crt"
readonly CA_KEY="${PKI_DIR}/ca.key"
readonly EXT="${PKI_DIR}/central.ext"
readonly LOCK="/run/lock/obstack-cert-renew.lock"
readonly COMPOSE_DIR="/opt/obstack"

exec 9>"$LOCK"
flock -n 9 || exit 0

for file in "$CERT" "$KEY" "$CA_CERT" "$CA_KEY" "$EXT"; do
  if [[ ! -s "$file" ]]; then
    echo "Required certificate material is missing: $file" >&2
    exit 1
  fi
done

# Keep a 30-day safety window. The weekly timer renews well before expiry.
if openssl x509 -in "$CERT" -checkend 2592000 -noout >/dev/null 2>&1; then
  echo "Central TLS certificate remains valid for more than 30 days; no renewal needed."
  exit 0
fi

if ! openssl x509 -in "$CA_CERT" -checkend 7776000 -noout >/dev/null 2>&1; then
  echo "Private CA certificate expires within 90 days; manual CA rotation is required." >&2
  exit 1
fi

tmp="$(mktemp -d "${PKI_DIR}/.renew.XXXXXX")"
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

openssl req -new -sha256 -key "$KEY" -out "$tmp/central.csr" \
  -subj "/CN=${OBSTACK_WG_VPN_IP}"
openssl x509 -req -sha256 -in "$tmp/central.csr" \
  -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$tmp/central.crt" -days 397 -extfile "$EXT"
openssl verify -CAfile "$CA_CERT" "$tmp/central.crt"
openssl x509 -in "$tmp/central.crt" -checkend 2592000 -noout

# Verify the renewed leaf uses the existing private key before installation.
openssl pkey -in "$KEY" -pubout -out "$tmp/key.pub"
openssl x509 -in "$tmp/central.crt" -pubkey -noout > "$tmp/cert.pub"
cmp -s "$tmp/key.pub" "$tmp/cert.pub" || {
  echo "Renewed certificate does not match the configured private key." >&2
  exit 1
}

cp -a "$CERT" "$tmp/central.crt.previous"
install -o root -g obstack-nginx -m 0640 "$tmp/central.crt" "${CERT}.new"
mv -f "${CERT}.new" "$CERT"

rollback() {
  install -o root -g obstack-nginx -m 0640 "$tmp/central.crt.previous" "${CERT}.rollback"
  mv -f "${CERT}.rollback" "$CERT"
  docker compose exec -T nginx nginx -t &&
    docker compose exec -T nginx nginx -s reload || true
}
if ! docker compose -f "$COMPOSE_DIR/compose.yaml" exec -T nginx nginx -t; then
  echo "Nginx rejected renewed certificate; restoring previous certificate." >&2
  rollback
  exit 1
fi
if ! docker compose -f "$COMPOSE_DIR/compose.yaml" exec -T nginx nginx -s reload; then
  echo "Nginx reload failed; restoring previous certificate." >&2
  rollback
  exit 1
fi

echo "Central TLS certificate renewed and Nginx reloaded successfully."
