#!/bin/sh
set -eu

CERT_PATH="${PROXY_TLS_CERT_PATH:-/certs/tls.crt}"
KEY_PATH="${PROXY_TLS_KEY_PATH:-/certs/tls.key}"
TLS_COMMON_NAME="${PROXY_TLS_COMMON_NAME:-${VLESS_COMPAT_DOMAIN:-localhost}}"
WS_UPSTREAM_HOST="${PROXY_WS_UPSTREAM_HOST:-host.docker.internal}"
WS_UPSTREAM_PORT="${PROXY_WS_UPSTREAM_PORT:-8444}"
API_UPSTREAM_HOST="${PROXY_API_UPSTREAM_HOST:-api}"
API_UPSTREAM_PORT="${PROXY_API_UPSTREAM_PORT:-8080}"

if [ -n "${VLESS_COMPAT_HASH:-}" ]; then
  COMPAT_HASH="${VLESS_COMPAT_HASH}"
elif [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  COMPAT_HASH="$(printf '%s' "${TELEGRAM_BOT_TOKEN}" | sha256sum | awk '{print substr($1, 1, 8)}')"
else
  COMPAT_HASH="vpnbot00"
fi

COMPAT_WS_PATH="${VLESS_COMPAT_PATH:-}"
if [ -z "$COMPAT_WS_PATH" ]; then
  COMPAT_WS_PATH="/ws$COMPAT_HASH"
else
  COMPAT_WS_PATH="$(printf '%s' "$COMPAT_WS_PATH" | sed "s/{hash}/$COMPAT_HASH/g")"
fi

COMPAT_SUB_PATH="${VLESS_COMPAT_SUB_PATH:-}"
if [ -z "$COMPAT_SUB_PATH" ]; then
  COMPAT_SUB_PATH="/pac$COMPAT_HASH/sub"
else
  COMPAT_SUB_PATH="$(printf '%s' "$COMPAT_SUB_PATH" | sed "s/{hash}/$COMPAT_HASH/g")"
fi

if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
  mkdir -p "$(dirname "$CERT_PATH")" "$(dirname "$KEY_PATH")"
  openssl req \
    -x509 \
    -nodes \
    -newkey rsa:2048 \
    -days "${PROXY_SELF_SIGNED_DAYS:-365}" \
    -keyout "$KEY_PATH" \
    -out "$CERT_PATH" \
    -subj "/CN=${TLS_COMMON_NAME}"
fi

export CERT_PATH
export KEY_PATH
export COMPAT_WS_PATH
export COMPAT_SUB_PATH
export WS_UPSTREAM_HOST
export WS_UPSTREAM_PORT
export API_UPSTREAM_HOST
export API_UPSTREAM_PORT

envsubst '${CERT_PATH} ${KEY_PATH} ${COMPAT_WS_PATH} ${COMPAT_SUB_PATH} ${WS_UPSTREAM_HOST} ${WS_UPSTREAM_PORT} ${API_UPSTREAM_HOST} ${API_UPSTREAM_PORT}' \
  < /etc/nginx/templates/nginx.conf.template \
  > /etc/nginx/nginx.conf

exec nginx -g 'daemon off;'
