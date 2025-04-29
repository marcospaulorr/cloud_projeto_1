# Projeto 1 - Aplicação Cloud

Este projeto implementa uma API RESTful para cadastro e autenticação de usuários, além de consulta de dados externos (Bovespa).

## Tecnologias Utilizadas

- FastAPI
- PostgreSQL
- Docker
- AWS Lightsail (próxima etapa)

## Como Executar

### Localmente com Docker Compose

1. Certifique-se de ter o Docker e Docker Compose instalados
2. Clone este repositório
3. Execute o comando: `docker compose up -d`
4. Acesse a API em: http://localhost:8000
5. Acesse a documentação em: http://localhost:8000/docs

### Endpoints da API

- `POST /registrar` - Cadastra um novo usuário
- `POST /login` - Autentica um usuário existente
- `GET /consultar` - Consulta dados da Bovespa (requer autenticação)

## Publicação no Docker Hub

```bash
docker build -t seuusername/insper-cloud-api:latest .
docker push seuusername/insper-cloud-api:latest