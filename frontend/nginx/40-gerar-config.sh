#!/bin/sh
# Gera o js/config.js com o endereço da API definido na variável API_URL.
# Assim, o mesmo container funciona com qualquer endereço de API, sem
# precisar reconstruir a imagem: basta mudar API_URL no docker-compose.yml.
set -eu

ARQUIVO=/usr/share/nginx/html/js/config.js

printf '// Gerado ao iniciar o container (frontend/nginx/40-gerar-config.sh).\nexport const API_URL = "%s";\n' "$API_URL" > "$ARQUIVO"

echo "config.js gerado com API_URL=$API_URL"
