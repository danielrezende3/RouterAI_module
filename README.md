# SmartRoute - RouterAI_module

Este projeto visa criar o módulo RouterAI, que integra múltiplas APIs de IA e roteia requisições para oferecer o melhor serviço aos usuários.

## Instalar e rodar o projeto

Para rodar o projeto, é preciso ter o poetry instaldo, Se você não tem, instale seguindo as instruções da [documentação](https://python-poetry.org/docs/).

### Dependências locais

Utilize o Poetry para gerenciar as dependências do projeto:

Gere o arquivo `poetry.lock`:

```bash
poetry lock
```

Instale as dependências:

```bash
poetry install
```

### Configurar o banco de dados

```bash
docker run --name my_postgres -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres
docker exec -it my_postgres psql -U postgres -c "CREATE DATABASE chat_history;"
```


### Iniciar o Ambiente Virtual com Poetry

Entre no ambiente virtual do Poetry:

```bash
poetry shell
```

### Configurar o Arquivo .env

Configure o arquivo `.env` com as variáveis de ambiente necessárias. Envie as chaves apropriadas conforme orientações do time.

```dotenv
OPENAI_API_KEY=ADD_KEY_HERE
ANTHROPIC_API_KEY=ADD_KEY_HERE
GEMINI_API_KEY=ADD_KEY_HERE
```

### Rodar o projeto

```bash
fastapi dev smartroute/main.py
```

Isto irá iniciar o servidor FastAPI na porta 8000. Acesse `http://localhost:8000/docs` para visualizar a documentação da API.
