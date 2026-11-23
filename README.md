
<div id="top"></div>

<div align="center">

# ArteBot

**Telegram AI Bot | Gemini LLM | RAG**

<img src="https://img.shields.io/badge/Python-3776AB.svg?style=for-the-badge&logo=Python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/Google-Gemini-4285F4.svg?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Google Gemini">
<img src="https://img.shields.io/badge/Telegram-Bot-26A5E4.svg?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">

</div>

<br>

---

## Overview

**ArteBot** 
- Integração do bot via telegram, grupo de chat direto com usuário.
- LLM definido Gemini, versão modelo default 'gemini-3.5-flash'. Adotado por menor custo e resultado. Via chat telegram possível definir versão na 'descrition' do grupo.
- Histórico do chat via sqlite, mantendo contexto do chat, filtro chat/today. 
Limitado:
- Não está tratando any casos,somente focado no resultado scopo do desafio.
- Bot limitado ao RAG de informações. 
- As respostas nao estão seguindo um padrão(formato,campos,linhas),podendo variar. SYSTEM instruction baseado no resuldado da tarefa.

### Evoluções futuras
- **Voice/Text:** Transcrição de voice para texto.
- **Loop Chat:** Implementação limitar interação do cliente, redirect para suporte.
- **Context:** Separação do contexto por assunto e grupo.
- **dbVector:** Implementação de banco vetorial para recuperação semântica.
- **Embedded:** Utilização de collections e embeddings para melhorar a recuperação contextual.
- **Redirect:** Implementação de respostas de redirecionamento.
- **LangSmith:** Integrar com dash LangSmith, monitor de tokens,historico model,cost,time runnnig,etc. 
---

## Tools
- VS Code, Plugins de assistência code,Claude,Gemini.
---

## Instructions
### 1. Gemini Auth

É necessário configurar uma credencial de acesso à API do Google Gemini.

GEMINI_API_KEY=your_gemini_api_key
Ou
VERTEX_API_KEY=your_vertex_api_key

GEMINI_API_KEY - Requisito voice/text
VERTEX_API_KEY - Conta GCP configurado billing.

O projeto utiliza `os.getenv()` para recuperar as credenciais do ambiente.

## Dependencias: 
- python 3.11+
- pip install -r requirements.txt

## 1 Test via terminal: 
- python arte_bot.py --prompt 'Quais opções de violões disponíveis custando até R$1000?'

## 2 Test via telegram: 
### Telegram Bot
- É necessário criar um bot no Telegram e configurar seu token de acesso.
- Variável de ambiente: TELEGRAM_TOKEN_0=your_telegram_bot_token
- Criar grupo telegram add novo Bot, set admin permission.
- python app.py 
#### How to Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://telegram.me/BotFather).
2. Tap **Start**.
3. Send the `/newbot` command.
4. Enter a display name for your bot.
5. Enter a unique username ending in `bot` (for example, `my_example_bot`).
6. Copy and securely store the HTTP API token provided by BotFather.
7. Configure the token in the `TELEGRAM_TOKEN_0` environment variable.

**Important:** Never expose API keys or bot tokens in your source code or public GitHub repository.

---
## Demo

<div align="center">

<a href="https://t.me/+i8VkRl4AkvkxYTQx">
<img src="https://img.shields.io/badge/Telegram-Access%20ArteBot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="ArteBot Telegram Access">
</a>

</div>

---

<div align="right">

[⬆ Back to Top](#top)

</div>
