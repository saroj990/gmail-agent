# Web UI

SvelteKit (Svelte 5) single-page app for the Gmail AI Inbox Agent. It talks to the
FastAPI server in [`app/server.py`](../app/server.py).

Requires Node from the repo's [`.nvmrc`](../.nvmrc) (`nvm use`) and pnpm.

```bash
pnpm install
pnpm dev      # http://localhost:5173, proxies /api to http://127.0.0.1:8000
pnpm build    # outputs build/, served by `python main.py serve`
pnpm check    # svelte-check / TypeScript
```

During development run the API in another terminal from the repo root:

```bash
python main.py serve
```

Pages:

- `/login`: Google sign-in (opens the consent page in your browser).
- `/`: dashboard with dry run, real run, approving dry-run results, and history.
- `/preferences`: classifier, label, threshold, and emails-per-run settings.
