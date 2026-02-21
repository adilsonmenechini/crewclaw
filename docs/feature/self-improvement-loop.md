# Feature: Self-Improvement Loop (Auto-Refactoring)

Este recurso permite que o agente analise seu próprio desempenho e sugira melhorias no código-fonte ou em seus próprios prompts.

## Ciclo de Auto-Melhoria

1.  **Análise de Logs**: O agente revisa arquivos em `logs/` para identificar falhas de ferramentas ou alucinações.
2.  **Proposta de Correção**: O agente cria um `implementation_plan.md` interno para corrigir o problema.
3.  **Execução**: Usando as ferramentas `file_write` e `shell` (para testes), o agente aplica a correção.
4.  **Verificação**: O agente roda o `pytest` para garantir que não houve regressão.

## Exemplo de Aplicação
Se uma ferramenta de `web_search` falha repetidamente por mudança na API, o agente pode tentar atualizar a URL base ou sugerir uma biblioteca alternativa via `pip install`.

## Controles de Segurança
Este recurso é desabilitado por padrão e requer o flag `--allow-self-improvement` para operar, devido ao alto risco de alterações não supervisionadas no código.
