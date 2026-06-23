#!/usr/bin/env bash
#
# Maskan — bitta buyruqli deploy skripti.
#
# Serverda (root sifatida) ishga tushiring:
#   sudo bash deploy.sh
#
# Nima qiladi (ketma-ket, bittada):
#   1) Git'dan eng so'nggi kodni tortadi (git pull)
#   2) Docker konteynerlarni qayta quradi va ishga tushiradi (web, bot, webapp, db)
#   3) app.mas-kan.uz uchun DNS yozuvini tekshiradi
#   4) app.mas-kan.uz uchun Let's Encrypt SSL sertifikatini oladi (yo'q bo'lsa)
#   5) nginx vhostni ulaydi va qayta yuklaydi
#
# DIQQAT: DNS A yozuvini (app -> server IP) domen panelida QO'LDA qo'shasiz.
#         Skript uni qo'sha olmaydi, faqat tekshiradi.
#
set -euo pipefail

# ----------------------------------------------------------------------------
# Sozlamalar
# ----------------------------------------------------------------------------
DOMAIN="app.mas-kan.uz"
UPSTREAM_PORT="8010"                 # webapp konteyneri host portida (docker-compose)
EMAIL="azizovsokhibkhon@gmail.com"   # Let's Encrypt bildirishnomalari uchun
WEBROOT="/var/www/certbot"
SITES_AV="/etc/nginx/sites-available"
SITES_EN="/etc/nginx/sites-enabled"
CONF_NAME="$DOMAIN"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ----------------------------------------------------------------------------
# Yordamchilar
# ----------------------------------------------------------------------------
red() { printf '\033[31m%s\033[0m\n' "$*"; }
grn() { printf '\033[32m%s\033[0m\n' "$*"; }
ylw() { printf '\033[33m%s\033[0m\n' "$*"; }
hdr() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { red "Root kerak. Ishga tushiring:  sudo bash $0"; exit 1; }

# docker compose (v2) yoki docker-compose (v1) ni aniqlash
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  red "docker compose topilmadi."; exit 1
fi

cd "$REPO_DIR"

# ----------------------------------------------------------------------------
# 1) Kodni yangilash
# ----------------------------------------------------------------------------
hdr "1/5  Git'dan so'nggi kod tortilyapti"
if [ -d .git ]; then
  git pull --ff-only || ylw "git pull o'tkazib yuborildi (lokal o'zgarishlar bormi?)."
else
  ylw "Bu papka git repo emas — git pull o'tkazib yuborildi."
fi

# ----------------------------------------------------------------------------
# 2) Docker konteynerlarni qayta qurish va ishga tushirish
# ----------------------------------------------------------------------------
hdr "2/5  Docker konteynerlar qayta qurilyapti (production)"
$DC -f docker-compose.yml -f docker-compose.prod.yml up -d --build
grn "✓ Konteynerlar ishga tushdi (tariflar + webapp yangilandi)."

# ----------------------------------------------------------------------------
# 3) DNS tekshiruvi
# ----------------------------------------------------------------------------
hdr "3/5  DNS tekshirilyapti: $DOMAIN"
SERVER_IP="$(curl -s --max-time 10 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')"
DNS_IP="$(getent hosts "$DOMAIN" | awk '{print $1}' | head -1 || true)"

if [ -z "$DNS_IP" ]; then
  red "✗ $DOMAIN uchun DNS yozuvi YO'Q (NXDOMAIN)."
  ylw "  Domen panelida (Cloudflare/registrar) quyidagi A yozuvni qo'shing:"
  ylw "       Type: A   Name: app   Value: $SERVER_IP"
  ylw "  So'ng (5–30 daqiqadan keyin) shu skriptni qayta ishga tushiring."
  exit 1
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
  ylw "⚠ $DOMAIN -> $DNS_IP, lekin server IP -> $SERVER_IP (mos emas)."
  ylw "  DNS hali to'liq tarqalmagan bo'lishi mumkin — sertifikat olishda xato chiqishi mumkin."
else
  grn "✓ DNS to'g'ri: $DOMAIN -> $DNS_IP"
fi

mkdir -p "$WEBROOT"

# ----------------------------------------------------------------------------
# 4) SSL sertifikat
# ----------------------------------------------------------------------------
hdr "4/5  SSL sertifikat: $DOMAIN"
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  grn "✓ Sertifikat allaqachon mavjud — qayta olinmadi."
else
  command -v certbot >/dev/null 2>&1 || { ylw "certbot o'rnatilyapti..."; apt-get update -qq && apt-get install -y certbot; }

  # ACME challenge uchun vaqtinchalik HTTP-only vhost
  cat > "$SITES_AV/$CONF_NAME" <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root $WEBROOT; }
    location / { return 404; }
}
EOF
  ln -sf "$SITES_AV/$CONF_NAME" "$SITES_EN/$CONF_NAME"
  nginx -t && systemctl reload nginx

  certbot certonly --webroot -w "$WEBROOT" -d "$DOMAIN" \
      --non-interactive --agree-tos -m "$EMAIL"
  grn "✓ Sertifikat olindi."
fi

# ----------------------------------------------------------------------------
# 5) To'liq nginx vhost (HTTPS + proxy) — repodagi nginx/webapp.conf
# ----------------------------------------------------------------------------
hdr "5/5  nginx vhost o'rnatilyapti (HTTPS -> 127.0.0.1:$UPSTREAM_PORT)"
cp "$REPO_DIR/nginx/webapp.conf" "$SITES_AV/$CONF_NAME"
ln -sf "$SITES_AV/$CONF_NAME" "$SITES_EN/$CONF_NAME"
nginx -t && systemctl reload nginx

grn ""
grn "=============================================================="
grn " ✓ TAYYOR!  Endi tekshiring:  https://$DOMAIN/login"
grn "=============================================================="
