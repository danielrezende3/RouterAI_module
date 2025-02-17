# SmartRoute - RouterAI_module

This project contains its to create RouterAI module, which integrates multiple AI APIs and routes requests to provide users with the best service for their needs.

## overview

Este projeto visa criar um módulo API capaz de direcionar dinamicamente as requisições para diferentes provedores de inteligência artificial – especificamente, [Chatgpt](https://chatgpt.com/), [Gemini](https://gemini.google.com/?hl=pt-BR), [Claude](https://claude.ai/)  [Deepseek](https://www.deepseek.com/), [mistral](https://x.ai/) e [grok](https://x.ai/)– com base em critérios de fallback, sendo eles custo, latência, disponibilidade e qualidade da resposta. A ideia central é garantir disponibilidade e tolerância a falhas, permitindo que o sistema se adapte a diferentes cenários de carga e variações na performance dos provedores.

O módulo proporciona uma solução robusta, simples e de fácil manutenção. A arquitetura proposta tem como foco oferecer um sistema de roteamento inteligente que beneficie tanto outros times de engenharia quanto sistemas internos, otimizando o uso dos recursos e melhorando a experiência dos usuários finais.

Este documento destina-se a oferecer uma visão clara do problema, das soluções consideradas e do plano de execução, para que todos possam entender e, se necessário, contribuir com feedback ou implementação.

## Como medir custo, latência, disponibilidade e qualidade da resposta?

### Custo

- Monitorar o valor gasto por requisição ou por período, considerando o modelo de cobrança de cada provedor.
- Registrar e comparar o custo das chamadas API realizadas para cada provedor, possibilitando a criação de métricas de custo médio e total.

### Disponibilidade

- Implementar mecanismos de fallback, retry e circuit breaker para lidar com indisponibilidade temporária de provedores.
  - Fallback: Ir para outro provedor se o primeiro falhar
  - Retry: Tentar de novo o mesmo provedor se algo falhar.
  - Circuit Breaker: Um "disjuntor" que desliga as tentativas quando algo falha muitas vezes seguidas, evitando piorar a situação.
- Realizar testes de stress e de falhas simuladas para validar a resiliência do sistema.
- Monitorar a taxa de erros e quedas, definindo métricas que permitam identificar rapidamente falhas críticas e disparar alertas.

### Qualidade da resposta

- Utilização de sites como [Artificial Analysis](https://artificialanalysis.ai/) para medir a qualidade, preço e velocidade
- Utilização de modelos como [nvidia/prompt-task-and-complexity-classifier](https://huggingface.co/nvidia/prompt-task-and-complexity-classifier) para classificação de respostas para modelos adequados

## Milestones

### Versão 1

Permite enviar um texto para diferentes LLMs com fallback automático.

**POST /generate-response**

```json
{
  "text": "bom dia"
}
```

Saída, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "gemini"
}
```

Saída, (todos os fallbacks falharam)

```json
{
  "error": "Não foi possível concluir a chamada",
}
```

### Versão 2

Permite definir qual tipo de fallback, sendo eles:

1. Custo
2. Disponibilidade, checar o status.site-do-llm.com
3. Qualidade da resposta

**POST /generate-response**

```json
{
  "text": "bom dia",
  "type-rollback": "cost" | "latency" | "availability" | "quality"
}
```

Saída, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "grok"
}
```

### Versão 3

Permite definir a ordem de fallback das LLMs.

Atenção ao detalhe em que é possível escolher o fallback ou o seu tipo, **NUNCA** os dois

**POST /generate-response**

```json
{
  "text": "bom dia",
  "fallback": ["chatgpt", "deepseek"]
}
```

Saida, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "deepseek"
}
```

### Versão 4

Permite enviar texto junto com arquivos (PDF ou imagem) para processamento.

**POST /generate-content** (validar se é realmente um arquivo pdf ou imagem.)

```json
{
  "text": "Analise esta imagem para mim e gere uma imagem resultante",
  "file_path": ["file=@caminho/do/arquivo.pdf", "file=@caminho/do/arquivo2.png"]
}
```

Saida, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "output-image": "image_path",
  "model-used": "mistral"
}
```

### Versão 5

Permite selecionar as LLMs por fallback ao processar texto + arquivos.

**POST /generate-content**

```json
{
  "text": "Desenhe uma maça caindo do céu",
  "file_path": ["file=@caminho/do/arquivo.pdf", "file=@caminho/do/arquivo2.png"],
  "fallback": ["chatgpt", "deepseek"]
}
```

Saída, caminho feliz

```json
{
  "output": "",
  "output-image": "file=@caminho/do/arquivo.png",
  "model-used": "mistral"
}
```

### Versão 6

Além de enviar o arquivo, permite selecionar as LLM's por tipo de fallback. Atenção que ao usar `type-rollback`, não será possível usar `fallback`

**POST /generate-content**

```json
{
  "text": "Desenhe uma maça caindo do céu",
  "file_path": ["file=@caminho/do/arquivo.pdf", "file=@caminho/do/arquivo2.png"],
  "type-rollback": "cost" | "latency" | "availability" | "quality"
}
```

Saída, caminho feliz

```json
{
  "output": "",
  "output-image": "file=@caminho/do/arquivo.png",
  "model-used": "mistral"
}
```

### Versão xx - usuário autenticado

- Tokens?
- usuário e senha?

### Versão xx - Monitoramento

- logger?
- excel?
- planilha interativa (powerbi)?
