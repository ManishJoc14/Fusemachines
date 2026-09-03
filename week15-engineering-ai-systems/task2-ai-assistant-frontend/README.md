# Engineering AI Assistant Frontend

A Next.js interface for the FastAPI AI assistant. It provides Google sign-in,
server-backed chat sessions, document uploads, streaming answers, visible tool
activity, citations, Markdown, math, code highlighting, and Mermaid diagrams.

## Local development

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Configure these values:

```env
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-web-client-id
NEXT_PUBLIC_API_URL=/backend/api/v1
```

Install and start the frontend:

```powershell
yarn install
yarn dev
```

Open <http://localhost:3000>. The `/backend` rewrite proxies browser requests
to FastAPI, allowing its HttpOnly session cookie to remain first-party.

## Google OAuth configuration

Create a Web application OAuth client and add the frontend URL to its
authorized JavaScript origins:

```text
http://localhost:3000
https://your-production-domain.example
```

Use the same client ID for `NEXT_PUBLIC_GOOGLE_CLIENT_ID` in the frontend and
`GOOGLE_CLIENT_ID` in the backend.

## Production verification

```powershell
yarn next typegen
yarn typecheck
yarn lint
yarn build
```

## Docker deployment

The backend Compose file builds the complete stack, including this frontend:

```powershell
cd ../task1-ai-assistant-backend
docker compose up -d --build
```

Before hosting, configure the backend `.env` with production credentials and:

```env
GOOGLE_CLIENT_ID=your-google-web-client-id
AUTH_COOKIE_SECURE=true
CORS_ORIGINS='["https://your-production-domain.example"]'
```

Expose the frontend on HTTPS. Keep PostgreSQL and Redis private, and avoid
exposing FastAPI publicly when all browser traffic uses the frontend rewrite.

The optional vLLM service is not started unless the `local` Compose profile is
explicitly enabled.
