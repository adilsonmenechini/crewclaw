# Feature: Heartbeat Scheduler (Proatividade)

Este recurso introduz a capacidade de execução proativa no CrewClaw, permitindo que o agente "desperte" e realize tarefas sem intervenção humana direta.

## Funcionamento

Um serviço de background (Heartbeat) executa em intervalos configuráveis e aciona o Agent Loop.

### Casos de Uso
1.  **Monitoramento Ativo**: Verificar status de deploys ou logs de erro a cada 10 minutos.
2.  **Daily Standup**: O agente analisa o trabalho feito no dia anterior e prepara um resumo às 9h da manhã.
3.  **Limpeza e Manutenção**: Refatoração de memória e compactação de logs durante a madrugada.

## Configuração (`crewclaw.json`)

```json
{
  "scheduler": {
    "enabled": true,
    "heartbeat_interval_seconds": 3600,
    "tasks": [
      {
        "name": "daily_summary",
        "cron": "0 9 * * *",
        "agent": "manager",
        "task": "Gerar resumo das atividades das últimas 24h"
      }
    ]
  }
}
```

## Arquitetura
O Heartbeat utiliza o `Runtime` ReAct existente, mas injeta estímulos temporais ou baseados em eventos invés de apenas mensagens de usuário.
