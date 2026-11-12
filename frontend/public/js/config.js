// Endereço da API, visto pelo navegador.
// No container, este arquivo é substituído ao iniciar (nginx/40-gerar-config.sh)
// com o valor da variável API_URL do docker-compose.yml. Este valor só vale
// para quem roda o frontend sem Docker.
export const API_URL = "http://localhost:8000/api";
