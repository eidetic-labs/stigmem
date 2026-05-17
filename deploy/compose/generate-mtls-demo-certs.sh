#!/usr/bin/env sh
set -eu

TLS_DIR="${1:-deploy/compose/tls}"
mkdir -p "$TLS_DIR"

openssl genpkey -algorithm ed25519 -out "$TLS_DIR/ca.key"
openssl req -new -x509 -key "$TLS_DIR/ca.key" -out "$TLS_DIR/ca.crt" -days 3650 \
  -subj "/CN=Stigmem Compose Federation CA"

generate_node_cert() {
  name="$1"
  dns_name="$2"
  entity_uri="$3"

  openssl genpkey -algorithm ed25519 -out "$TLS_DIR/${name}.key"
  openssl req -new -key "$TLS_DIR/${name}.key" -out "$TLS_DIR/${name}.csr" \
    -subj "/CN=${dns_name}"
  {
    printf 'subjectAltName=DNS:%s,URI:%s\n' "$dns_name" "$entity_uri"
    printf 'extendedKeyUsage=serverAuth,clientAuth\n'
  } > "$TLS_DIR/${name}.ext"
  openssl x509 -req -in "$TLS_DIR/${name}.csr" \
    -CA "$TLS_DIR/ca.crt" -CAkey "$TLS_DIR/ca.key" -CAcreateserial \
    -out "$TLS_DIR/${name}.crt" -days 90 -extfile "$TLS_DIR/${name}.ext"
  rm -f "$TLS_DIR/${name}.csr" "$TLS_DIR/${name}.ext"
}

generate_node_cert "node-a" "stigmem-a" "stigmem://compose/node-a"
generate_node_cert "node-b" "stigmem-b" "stigmem://compose/node-b"

chmod 600 "$TLS_DIR"/*.key

cat <<EOF
Generated mTLS demo certificate material in $TLS_DIR

Start the mTLS federation example with:
  docker compose -f deploy/compose/docker-compose.mtls.yml up -d --build
EOF
