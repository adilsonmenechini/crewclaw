# Feature: Multi-channel Messenger Bridge

Este recurso expande a interface do CrewClaw para além do Terminal, permitindo interação via aplicativos de mensagens.

## Arquitetura de Canais

O CrewClaw introduz uma camada de `Channel` abstrata:

```python
class BaseChannel:
    def send_message(self, text, user_id): pass
    def receive_message(self): pass
```

### Implementações Propostas
1.  **TelegramChannel**: Integração via Bot API.
2.  **WhatsAppChannel**: Integração via Twilio ou gateways locais.
3.  **SlackChannel**: Integração via Bolt SDK.

## Workflow de Interação
1.  Usuário envia mensagem no Telegram: "/run explorer Analise o repo".
2.  O `MultiChannelBridge` traduz a mensagem para o formato interno do `AgentLoop`.
3.  O agente executa as ferramentas localmente.
4.  O resultado é enviado de volta como uma mensagem de chat rica (com formatação Markdown).

## Segurança (SSRF & Sandbox)
Ao abrir canais externos, o CrewClaw reforça os checks de segurança para evitar que comandos maliciosos sejam injetados via chat externo.
