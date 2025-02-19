# Tutorial de Configuração do Projeto

Este tutorial irá guiá-lo pelo processo de configuração do ambiente de desenvolvimento para o projeto.

## Passo 1: Verificar a Versão do Python

Certifique-se de que a versão do Python instalada seja ^3.12.

- **Se não for a versão correta:**
  - Instale o [pyenv](https://github.com/pyenv/pyenv).
  - Configure a versão desejada como global.

```bash
pyenv install 3.12.x
pyenv global 3.12.x
```

## Passo 2: Clonar o Repositório e Mudar para a Branch Correta

Clone o repositório e, em seguida, mude para a branch de desenvolvimento ou outra branch necessária.

```bash
git clone https://seu-repositorio.git
cd nome-do-repositorio
git checkout nome-da-branch
```

## Passo 3: Instalar Dependências com Poetry

Utilize o Poetry para gerenciar as dependências do projeto:

1. Gere o arquivo `poetry.lock`:
   ```bash
   poetry lock
   ```
2. Instale as dependências:
   ```bash
   poetry install
   ```

## Passo 4: Iniciar o Ambiente Virtual com Poetry e Configurar o VSCode

Entre no ambiente virtual do Poetry e ajuste a versão do Python no VSCode:

```bash
poetry shell
```

- **No VSCode:**
  - Abra a paleta de comandos (`Ctrl+Shift+P` ou `Cmd+Shift+P`).
  - Selecione `Python: Select Interpreter` e escolha a versão do Python definida pelo Poetry.

## Passo 5: Configurar o Arquivo .env

Configure o arquivo `.env` com as variáveis de ambiente necessárias. Envie as chaves apropriadas conforme orientações do time.

```dotenv
# Exemplo de arquivo .env
SECRET_KEY=suachaveaqui
DATABASE_URL=postgres://usuario:senha@localhost:5432/seubanco
```

## Passo 6: Aprender FastAPI

Familiarize-se com o [FastAPI](https://fastapi.tiangolo.com/) para desenvolver a API do projeto. Alguns recursos úteis:

- [Documentação Oficial](https://fastapi.tiangolo.com/)
- [Tutorial Rápido](https://fastapi.tiangolo.com/tutorial/)
