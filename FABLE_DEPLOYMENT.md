<!-- SPDX-License-Identifier: CC-BY-NC-SA-4.0 -->

# Deploy Fable on Railway

Use one Railway project with three services in the same production environment and region. The website includes its own Discord OAuth and settings backend. It shares MongoDB with the bot and does not use the bot's legacy FastAPI server.

| Service | Source | Access |
| --- | --- | --- |
| MongoDB | Railway's MongoDB template with its persistent volume | Private network |
| Fable bot | `lspdfrzach/Fable`, branch `main`, repository root | Persistent worker, one replica, no public domain |
| Fable website | `lspdfrzach/Fable_frontend`, branch `main`, repository root | Public HTTPS, then `fablebot.xyz` |

The Dockerfiles and Railway configuration are in the repositories. Do not enable serverless sleeping or a cron schedule for the bot. Keep one bot replica so background tasks do not run twice.

## 1. Connect the account

Connect the Railway plugin to the Railway account that will own Fable. Railway's ChatGPT instructions say to start a new chat after installing and connecting it; select `@Railway` in that chat. GitHub integration must have access to both repositories. If Railway asks for a billing plan, review its displayed price and usage allowance before subscribing.

## 2. Create the database and services

Create a project named Fable and add MongoDB. Name the database service `MongoDB` so the variable references below match. Keep its persistent volume attached and use its private `MONGO_URL`; no public TCP proxy is required. Configure volume backups before retaining real community data.

Add both GitHub repositories as separate services. Name the bot `Fable-bot` and the website `Fable-website`. Select `main` and leave the root directory at the repository root. Both services build with Docker. Website health checks use `/api/health`; the bot is a worker and has no HTTP health check.

For a new installation use `DB_NAME=fable` in both services. If importing an existing database, use its actual database name in both instead.

## 3. Set private variables

Create shared Railway variables for `PRODUCTION_BOT_TOKEN`, `DISCORD_CLIENT_ID` and `DISCORD_CLIENT_SECRET` using values from the same Fable Discord application. Set these in Railway's Variables editor, never in the repository or chat. The application ID is public; the token and client secret are private.

Set the bot service variables:

```dotenv
ENVIRONMENT=PRODUCTION
PRODUCTION_BOT_TOKEN=${{shared.PRODUCTION_BOT_TOKEN}}
MONGO_URL=${{MongoDB.MONGO_URL}}
DB_NAME=fable
SYNC_COMMANDS=TRUE
COMMAND_GUILD_ID=0
INTERNAL_API_ENABLED=FALSE
```

Set the website service variables:

```dotenv
ENVIRONMENT=production
FABLE_BACKEND_MODE=builtin
DISCORD_CLIENT_ID=${{shared.DISCORD_CLIENT_ID}}
DISCORD_CLIENT_SECRET=${{shared.DISCORD_CLIENT_SECRET}}
DISCORD_BOT_TOKEN=${{shared.PRODUCTION_BOT_TOKEN}}
MONGO_URL=${{MongoDB.MONGO_URL}}
DB_NAME=fable
ORIGIN=https://YOUR-WEBSITE-DOMAIN
```

Generate a Railway domain for the website and replace `YOUR-WEBSITE-DOMAIN` with that exact hostname. Keep `ORIGIN` without a trailing slash or path. Railway supplies `PORT`; the website listens on `0.0.0.0`. Apply the staged variable changes by deploying.

Leave optional Turnstile, analytics, Maple County, weather and old ERM API variables unset unless those integrations have been configured. `BASE_API_URL` and `PANEL_API_URL` are not needed for this website. The bot's legacy API is disabled by default; `INTERNAL_API_ENABLED=TRUE` explicitly enables it for separately reviewed private integrations.

## 4. Configure Discord

In the Fable application at the Discord Developer Portal:

1. Enable the **Server Members** and **Message Content** privileged intents.
2. Keep **Installation > Install Link** set to **None**, as required by the upstream self-hosting restriction. Do not remove that restriction to work around setup.
3. Under **OAuth2 > Redirects**, register `https://YOUR-WEBSITE-DOMAIN/api/fable/Auth/Callback`. It must match the website's `ORIGIN` exactly.
4. Invite Fable to your server through the website's `/invite` route. The application must permit that installation. The invitation requests `bot` and `applications.commands`.
5. Start the bot. It now registers slash commands automatically. For a test server, `COMMAND_GUILD_ID` can be its ID; keep `0` for global registration. Global commands may take time to appear in Discord.
6. Run `/setup` in your server to create its settings, then configure management roles. The website only lists servers where Fable is already configured and your account has management access.

Bot-owner checks use Discord's application owner or eligible application-team members. There is no extra hard-coded owner account.

## 5. Verify, then connect the domain

- Bot logs must show MongoDB connected, all enabled extensions loaded and application commands registered. Confirm the bot appears online in Discord. Startup stops if the database or an extension fails.
- Check website `/`, `/login`, `/invite` and `/api/health`. Health confirms the web server and configuration, not a working Discord/MongoDB connection.
- Sign in with your own Discord account, select the configured server and change and restore a harmless basic setting. Verify the bot reads the same change.
- Start and end a test shift through Discord to verify database writes. Do not use a real staff record for a smoke test.
- Add `fablebot.xyz` to the website service. Apply the exact DNS records Railway supplies at your domain provider. Change website `ORIGIN` to `https://fablebot.xyz`, register `https://fablebot.xyz/api/fable/Auth/Callback` in Discord, then redeploy and repeat login on that hostname.

The included website backend supports login, guild selection, basic settings, anti-ping settings, shift configuration and documentation. Live web shift operations, moderation, applications, verification, game controls, billing and shard telemetry require additional backend work. The bot's own Discord commands are separate from these website capabilities. See the frontend's [backend guide](https://github.com/lspdfrzach/Fable_frontend/blob/main/docs/BACKEND.md).

Before accepting real website accounts, update the inherited terms and privacy pages to match Fable's actual operation. Keep upstream attribution and license notices. This deployment preparation does not verify real Discord credentials, live MongoDB access or domain ownership.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing token | Bot `ENVIRONMENT` is uppercase `PRODUCTION`, with `PRODUCTION_BOT_TOKEN` populated. |
| Database connection timeout | MongoDB is deployed and both services use its private reference in the same environment. |
| Install-link exception | Discord application Installation > Install Link is None. |
| No slash commands | Check the command-registration log, `SYNC_COMMANDS`, the bot's invite scopes and `COMMAND_GUILD_ID`. |
| Login unavailable or invalid redirect | Website secrets all belong to Fable; `ORIGIN` and Discord's registered callback match. |
| Server absent from website | Run `/setup`; confirm the same database name and your management permissions. |
| ER:LC requests fail | Authorize the bot host's outbound IP as described in `SELF_HOSTING.md`; do not guess it. |

## Verification commands

```bash
python -m pip install -r requirements.txt
python -m pip check
ENVIRONMENT=PRODUCTION PRODUCTION_BOT_TOKEN=fixture-token MONGO_URL=mongodb://localhost:27017/test python -m pytest -q
docker build -t fable-bot .
```

Tests use fixtures, not real tokens. GitHub Actions also builds the production container and runs tests inside it as the non-root runtime user.

References: [Railway ChatGPT plugin](https://docs.railway.com/ai/chatgpt-plugin), [MongoDB](https://docs.railway.com/databases/mongodb), [variables](https://docs.railway.com/variables), [config as code](https://docs.railway.com/config-as-code/reference).
