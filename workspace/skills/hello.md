---
name: "say_hello"
description: "Gera uma saudação personalizada e amigável."
parameters:
  name: "O nome da pessoa para saudar"
---

# Hello Skill
Uma skill simples de demonstração.

```python
def execute(name="User"):
    import datetime
    hour = datetime.datetime.now().hour
    greeting = "Bom dia"
    if 12 <= hour < 18:
        greeting = "Boa tarde"
    elif hour >= 18:
        greeting = "Boa noite"
        
    return f"{greeting}, {name}! Eu sou o seu assistente CrewClaw pronto para ajudar."
```
