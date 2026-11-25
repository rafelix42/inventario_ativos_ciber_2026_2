# Imagem do frontend do Inventário de Ativos de TI, que também é o proxy
# reverso de todo o sistema.
#
# O nginx escuta só HTTPS (443): serve os arquivos estáticos em / e encaminha
# /api/ para o container da API pela rede interna do Docker. Por isso deve
# rodar pelo docker-compose.yml, junto com o serviço 'api'.

FROM nginx:1.27-alpine

# openssl: gera um certificado autoassinado quando nenhum for fornecido.
RUN apk add --no-cache openssl

# Substitui o site padrão da imagem (que escuta na porta 80).
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Scripts em /docker-entrypoint.d/ rodam ao iniciar o container, antes do nginx.
# 'sed' remove um eventual CR (\r) caso o arquivo tenha sido salvo no Windows.
COPY nginx/30-certificado-tls.sh /docker-entrypoint.d/30-certificado-tls.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/30-certificado-tls.sh \
    && chmod +x /docker-entrypoint.d/30-certificado-tls.sh

COPY public /usr/share/nginx/html

# A API está na mesma origem, em /api. O js/config.js do repositório aponta
# para http://localhost:8000/api, usado só ao rodar o frontend sem Docker.
RUN printf '// Gerado na construção da imagem (frontend/Dockerfile).\nexport const API_URL = "/api";\n' \
    > /usr/share/nginx/html/js/config.js

EXPOSE 443

# --no-check-certificate: o certificado pode ser autoassinado.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider --no-check-certificate https://localhost/ || exit 1
