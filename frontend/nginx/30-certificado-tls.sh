#!/bin/sh
# Garante que exista um certificado TLS antes de o nginx iniciar.
#
# Em produção, coloque o certificado e a chave do servidor em certs/ no
# hospedeiro (montada em /etc/nginx/tls) com estes nomes:
#   certificado.pem  certificado + cadeia intermediária (ex.: fullchain.pem)
#   chave.pem        chave privada (ex.: privkey.pem)
#
# Se não existirem, gera um certificado autoassinado para desenvolvimento
# (o navegador mostra um aviso). Ele é gravado na própria pasta, então é
# reaproveitado nas próximas subidas do container.
set -eu

PASTA=/etc/nginx/tls
CERTIFICADO="$PASTA/certificado.pem"
CHAVE="$PASTA/chave.pem"

if [ -s "$CERTIFICADO" ] && [ -s "$CHAVE" ]; then
    echo "Certificado TLS encontrado em $PASTA."
    exit 0
fi

# Nomes aceitos pelo certificado: localhost por padrão, mais o que estiver em
# NOMES_DO_CERTIFICADO (ex.: "inventario.exemplo.br,192.168.0.10").
NOMES="DNS:localhost,IP:127.0.0.1,IP:::1"
for nome in $(echo "${NOMES_DO_CERTIFICADO:-}" | tr ',' ' '); do
    case "$nome" in
        *[!0-9.]*) NOMES="$NOMES,DNS:$nome" ;;
        *) NOMES="$NOMES,IP:$nome" ;;
    esac
done

echo "Certificado TLS não encontrado. Gerando um autoassinado ($NOMES)."
mkdir -p "$PASTA"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
    -days 365 -subj "/CN=localhost" -addext "subjectAltName=$NOMES" \
    -keyout "$CHAVE" -out "$CERTIFICADO" 2>/dev/null
chmod 600 "$CHAVE"
chmod 644 "$CERTIFICADO"

# Os arquivos ficam com o mesmo dono da pasta montada, para que o usuário do
# hospedeiro consiga substituí-los sem sudo.
chown "$(stat -c %u:%g "$PASTA")" "$CHAVE" "$CERTIFICADO"
