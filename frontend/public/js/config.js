// Endereço da API, visto pelo navegador.
// Na imagem Docker, este arquivo é substituído por API_URL = "/api" (a API
// fica na mesma origem, atrás do proxy; veja frontend/Dockerfile). Este valor
// só vale para quem roda o frontend sem Docker.
export const API_URL = "http://localhost:8000/api";
