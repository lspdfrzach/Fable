# Deploy the Fable bot from GitHub

This repository runs the Python Discord bot. Its bundled FastAPI server is for internal integrations; it does **not** implement the separate dashboard backend required by `Fable_frontend`.

## Railway setup

1. Create a Railway project and choose **Deploy from GitHub repo** → `lspdfrzach/Fable`. Select the branch containing this Dockerfile after reviewing the deployment pull request. Railway builds the Dockerfile and starts `python main.py`.
2. Add these variables in Railway's service **Variables** tab:
   - `ENVIRONMENT=PRODUCTION`
   - `PRODUCTION_BOT_TOKEN` = the token for your own Fable Discord application
   - `MONGO_URL` = your MongoDB connection string
   - `DB_NAME=fable` if you want a separate database from an ERM installation
   - `MC_API_URL` = your Maple County API base URL if that integration is in use
   - `MC_API_KEY` if the Maple County integration is in use
3. In the Discord Developer Portal, enable the Server Members and Message Content intents used by this bot. Its existing `setup_hook` rejects a publicly configured install link; follow the repository's `SELF_HOSTING.md` for the app installation settings.
4. Deploy the service and read its logs. The bot should connect to Discord and MongoDB. Do not enter tokens or the MongoDB URL in GitHub files, commits, issues, or pull requests.

Railway redeploys when commits reach the connected branch. Keep the service running as a persistent service, without a cron schedule. Do not add a public domain to the bot's API unless you have separately reviewed its authentication and access controls. For ER:LC private server API calls, follow `SELF_HOSTING.md` to authorize the host's outbound IP; that IP may change on some hosting plans.

## Dashboard status

`lspdfrzach/Fable_frontend` is a SvelteKit application that requires `VITE_INTERNAL_URL` pointing to ERM's separate, closed source backend. The Python bot's `utils/api.py` exposes a different set of endpoints and does not supply the frontend's Discord OAuth login, session, and dashboard endpoints. Hosting the frontend alone will display pages but will not make its account and management features work. Obtain or implement a compatible backend before configuring the frontend or linking `fablebot.xyz` to it.

## License

Preserve the upstream attribution and the repository license. The inherited CC BY-NC-SA terms limit commercial use of adaptations; review those terms before offering a paid Fable service.
