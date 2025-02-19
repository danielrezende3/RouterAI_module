# SmartRoute - RouterAI_module

This project contains its to create RouterAI module, which integrates multiple AI APIs and routes requests to provide users with the best service for their needs.

## overview

Este projeto visa criar um módulo API capaz de direcionar dinamicamente as requisições para diferentes provedores de inteligência artificial – especificamente, [Chatgpt](https://chatgpt.com/), [Gemini](https://gemini.google.com/?hl=pt-BR), [Claude](https://claude.ai/) – com base em critérios de fallback, sendo eles custo, latência e qualidade da resposta. A ideia central é garantir disponibilidade e tolerância a falhas, permitindo que o sistema se adapte a _diferentes cenários de carga (how?)_ e variações na performance dos provedores.

O módulo proporciona uma solução robusta, simples e de fácil manutenção. A arquitetura proposta tem como foco oferecer um sistema de roteamento inteligente que beneficie tanto outros times de engenharia quanto sistemas internos, otimizando o uso dos recursos e melhorando a experiência dos usuários finais.

Este documento destina-se a oferecer uma visão clara do problema, das soluções consideradas e do plano de execução, para que todos possam entender e, se necessário, contribuir com feedback ou implementação.

## Como medir custo, latência, disponibilidade e qualidade da resposta?

### Custo

- Monitorar o valor gasto por requisição ou por período, considerando o modelo de cobrança de cada provedor.
- Permitir utilização de diferentes modelos como nvidia/prompt-task-and-complexity-classifier para classificação de respostas de acordo com o custo.

### Disponibilidade

- Implementar mecanismo de fallback para lidar com indisponibilidade temporária de provedores.
- Permitir que o usuário escolha tiers de modelo, como fast, mid, reasoning e latency, para escolher o modelo mais adequado para a situação.
- Realizar testes de stress e de falhas simuladas para validar a resiliência do sistema.
- Monitorar a taxa de erros e quedas, definindo métricas que permitam identificar rapidamente falhas críticas e disparar alertas.

### Qualidade da resposta

- Utilização de sites como [Artificial Analysis](https://artificialanalysis.ai/) para medir a qualidade, preço e velocidade
- Utilização de modelos como [nvidia/prompt-task-and-complexity-classifier](https://huggingface.co/nvidia/prompt-task-and-complexity-classifier) para classificação de respostas para modelos adequados

## Milestones

### Feature/simple-fallback ✅

Permite enviar um texto para diferentes LLMs com fallback automático.

POST /v1/invoke

```json
{
  "input": "bom dia"
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

### Feature/nvidia-fallback ✅

Permite enviar um texto para nvidia classifier e enviar pro tier necessário.

POST /v1/invoke

```json
{
  "input": "bom dia"
}
```

Saída, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "gemini"
}
```

### Feature/tier-model ✅

Permite definir qual tipo de fallback, sendo eles:

1. Modelos rápidos e pequenos (fast)
1. Modelos medianos (mid)
1. Qualidade da resposta (reasoning)
1. Latência (latency)

POST /v1/invoke

```json
{
  "input": "bom dia",
  "tier-model": "fast" | "mid" | "reasoning" | "latency"
}
```

Saída, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "gemini"
}
```

### Feature/fallback-ordening ✅

Permite definir a ordem de fallback das LLMs.

Atenção ao detalhe em que é possível escolher o fallback ou o seu tipo, **NUNCA** os dois

POST /v1/invoke

```json
{
  "input": "bom dia",
  "fallback": ["chatgpt", "deepseek"]
}
```

ou POST /v1/invoke

```json
{
  "input": "bom dia",
  "tier-model": "fast" | "mid" | "reasoning" | "latency"
}
```

Saida, caminho feliz

```json
{
  "output": "bom dia Daniel",
  "model-used": "deepseek"
}
```

### Feature/send-image?

Permite enviar texto junto com arquivos (PDF ou imagem) para processamento.

POST /v1/invoke-image? (validar se é realmente um arquivo pdf ou imagem.)

```json
{
  "input": "Analise esta imagem para mim e gere uma imagem resultante",
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

### Feature/send-image-fallback

Permite selecionar as LLMs por fallback ao processar texto + arquivos.

POST /v1/invoke-image?

```json
{
  "input": "Desenhe uma maça caindo do céu",
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

### Feature/send-image-fallback-type

Além de enviar o arquivo, permite selecionar as LLM's por tipo de fallback. Atenção que ao usar `type-rollback`, não será possível usar `fallback`

POST /v1/invoke-image?

```json
{
  "input": "Desenhe uma maça caindo do céu",
  "file_path": ["file=@caminho/do/arquivo.pdf", "file=@caminho/do/arquivo2.png"],
  "tier-model": "fast" | "mid" | "reasoning" | "latency"
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

### Feature/nvidia-cpu-gpu

Make sure the API selects between gpu and cpu depending on the machine.

### Feature/nvidia-async

Make sure the API handle async `classifier.py` requests.

### Feature/RAG-simple

Send the documents, then the question and get the answer.
local storage, session or cookie, don't know which one is better.

### Feature/monitoring-db

Create a database to store the monitoring data.
