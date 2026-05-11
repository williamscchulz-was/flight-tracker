# Flight Tracker — NVT → MEX

Agente diário que checa voos NVT → Cidade do México (30/10/2026) via Google Flights, filtra por duração e preço, manda resumo no Discord. Pode rodar local (Windows Task Scheduler) ou na cloud (Claude Code Routines).

## Stack

- **Data**: `fast-flights` (consulta Google Flights, sem API key)
- **Runtime**: Windows Task Scheduler (local) **ou** Claude Code Routines (cloud)
- **Notificação**: Discord webhook (zero setup de bot)

## Parâmetros (no `flight_check.py`)

- NVT → MEX, 30/10/2026
- ≤16h, < R$3000/adulto
- Busca 1 adulto (preço puro); grupo 2A+1I = multiplica por ~2.1
- Top 5 mais baratos, embed bonito no Discord

## Setup

### 1. Discord webhook (~2 min)

1. Abre o servidor Discord onde quer receber. Se não tem servidor próprio, cria um privado só pra ti (free, 30s).
2. Cria/escolhe um canal (ex: `#flight-alerts`).
3. **Engrenagem do canal** → **Integrations** → **Webhooks** → **New Webhook**.
4. Dá um nome (ex: "Flight Bot"), avatar opcional → **Copy Webhook URL**.
5. Guarda essa URL — é tudo que precisa.

> Formato: `https://discord.com/api/webhooks/123.../abc...`

### 2. Repo GitHub

```bash
gh repo create flight-tracker --private
git clone https://github.com/williamscchulz-was/flight-tracker.git
cd flight-tracker
# joga flight_check.py, requirements.txt, README.md, .gitignore aqui
git add . && git commit -m "initial" && git push
```

### 3. Setup local (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

Copy-Item .env.example .env
# edita .env e cola a webhook real em DISCORD_WEBHOOK_URL

.\run.ps1
```

Se o embed chegou no canal, tá funcionando. `run.ps1` carrega `.env` automaticamente e usa o python do venv.

### 4. Rodar agendado via Task Scheduler (Windows)

```powershell
# Cria task que roda todo dia às 08:00
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\projetos\flight-tracker\run.ps1" `
            -WorkingDirectory "C:\projetos\flight-tracker"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "Flight Tracker NVT-MEX" `
    -Action $action -Trigger $trigger -Settings $settings -Description "Daily NVT->MEX flight check"
```

Pra testar sem esperar: `Start-ScheduledTask -TaskName "Flight Tracker NVT-MEX"`. Status: `Get-ScheduledTaskInfo -TaskName "Flight Tracker NVT-MEX"` — `LastTaskResult: 0` = ok, qualquer outra coisa = erro (vai postar embed vermelho no Discord também, se a webhook tiver válida).

### 5. Alternativa: Claude Code Routine (cloud)

1. `claude.ai/code/routines` → **New routine** → **Remote**.
2. Conecta o repo `flight-tracker`.
3. **Prompt**: cola o conteúdo de `routine_prompt.md`.
4. **Schedule**: Daily, 09:00 BRT (ou o horário que preferir).
5. **Environment → Allowed domains** (CRÍTICO):
   - `www.google.com` (Google Flights)
   - `discord.com` (webhook)
   - `pypi.org`, `files.pythonhosted.org` (geralmente já default, confirma)
6. **Secrets**:
   - `DISCORD_WEBHOOK_URL`
7. Salva → **Run now** pra testar.

## Notas

- **Sem API key, sem bot**. Webhook do Discord é uma URL única que aceita POST com JSON. Quem tem a URL pode mandar msg no canal — trata como senha.
- `fast-flights` depende do Google não mudar a API interna. Pra 1 chamada/dia, risco mínimo. Se quebrar, troca a `fetch_flights()` por SerpAPI ($50/mo).
- Erros do script (network, parsing) também viram embed vermelho no Discord — tu vai saber na hora.

## Extensões

- Rota de volta CUN → NVT: duplica repo OU adiciona segunda chamada/segundo embed no mesmo script
- Várias rotas (viagem US): refatora `CONFIG` pra ler JSON com lista de trechos
- Histórico de preços: Firestore ou SQLite pra detectar quedas relativas
