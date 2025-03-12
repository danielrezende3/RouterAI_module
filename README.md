# SmartRoute - RouterAI_module

Este projeto visa criar o módulo RouterAI, que integra múltiplas APIs de IA e roteia requisições para oferecer o melhor serviço aos usuários. Para mais dúvidas, acesse a página da [wiki](https://github.com/danielrezende3/RouterAI_module/wiki).

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

Infelizmente é preciso criar o banco de dados manualmente, pelo menos por enquanto, por dificuldades entre as bibliotecas langchain-postgres, sqlalchemy e  alembic.
```bash
docker run --name smartroute_db -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=chat_history -d -p 5432:5432 postgres
```

### Configurar o Arquivo .env

Configure o arquivo `.env` com as variáveis de ambiente necessárias. Envie as chaves apropriadas conforme orientações do time.

```dotenv
OPENAI_API_KEY=ADD_KEY_HERE
ANTHROPIC_API_KEY=ADD_KEY_HERE
GEMINI_API_KEY=ADD_KEY_HERE
DATABASE_URL="postgresql://postgres:mysecretpassword@localhost:5432/chat_history"
JWT_SECRET_KEY=ADD_PASSPHRASE_KEY_HERE
```

### Rodar o projeto

```bash
poetry run fastapi dev smartroute/main.py
```

Isto irá iniciar o servidor FastAPI na porta 8000. Acesse `http://localhost:8000/docs` para visualizar a documentação da API.
