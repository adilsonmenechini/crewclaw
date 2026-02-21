# Feature: Scheduled Hooks (Eventos Agendados)

Este recurso permite que o CrewClaw execute ações específicas baseadas em cronogramas ou eventos, funcionando como um sistema de "webhooks internos" ou gatilhos temporais.

## Diferença entre Heartbeat e Scheduled Hooks

- **Heartbeat**: Desperta o Agent Loop completo para raciocínio e execução de tarefas complexas (ex: "Analise os logs e me dê um resumo").
- **Scheduled Hooks**: Executa uma ação atômica e direta sem necessariamente envolver o Agent Loop de alto nível (ex: "Mande um POST para o Slack às 10h confirmando que o sistema está online").

## Definição de Hooks (`crewclaw.json`)

```json
{
  "hooks": [
    {
      "name": "health_check_ping",
      "schedule": "*/15 * * * *",
      "action": "webhook",
      "target": "https://monitor.meu-sre.com/ping",
      "payload": { "status": "ok", "agent": "crewclaw-01" }
    },
    {
      "name": "rotate_logs",
      "schedule": "0 0 * * *",
      "action": "shell",
      "target": "tar -czf logs/backup_$(date +%F).tar.gz logs/*.log && rm logs/*.log"
    }
  ]
}
```

## Tipos de Ações Suportadas

1.  **Webhook**: Envio de requisições HTTP (GET/POST).
2.  **Shell**: Execução de scripts ou comandos do sistema.
3.  **Log**: Registro de estado ou métricas em arquivos locais.
4.  **AgentTask**: Injeção de uma tarefa pré-definida no `AgentLoop`.

## Implementação Técnica
Os hooks são gerenciados por um `HookManager` que utiliza a biblioteca `schedule` ou `APScheduler` para garantir a execução precisa no tempo definido, operando em uma thread separada do loop principal de execução de agentes.
