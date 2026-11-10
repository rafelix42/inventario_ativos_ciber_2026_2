# Imagem do frontend do Inventário de Ativos de TI.
#
# Só arquivos estáticos (HTML, CSS e JavaScript), servidos pelo nginx. O
# navegador chama a API diretamente, no endereço informado em API_URL.
#
# Construir e executar (veja também ../docker-compose.yml):
#   docker build -t inventario-frontend .
#   docker run -p 8080:80 -e API_URL=http://localhost:8000/api inventario-frontend

FROM nginx:1.27-alpine

# Endereço da API visto pelo NAVEGADOR (não pela rede interna do Docker).
ENV API_URL=http://localhost:8000/api

# Arquivos em /etc/nginx/templates/ têm as variáveis de ambiente (${API_URL})
# substituídas ao iniciar o container e são gravados em /etc/nginx/conf.d/.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template

# Scripts em /docker-entrypoint.d/ rodam ao iniciar o container, antes do nginx.
# 'sed' remove um eventual CR (\r) caso o arquivo tenha sido salvo no Windows.
COPY nginx/40-gerar-config.sh /docker-entrypoint.d/40-gerar-config.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-gerar-config.sh \
    && chmod +x /docker-entrypoint.d/40-gerar-config.sh

COPY public /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
