# Length Lab

Length Lab is a full-stack measurement workspace with a Next.js + Tailwind frontend and a FastAPI backend.

## What it does

- Google login on the landing page
- Authenticated dashboard with nav bar, side bar, footer, and content area
- Measurement page that accepts up to 3 images
- Measurement results split into object cards and background cards
- Project naming and save flow backed by FastAPI storage

## Structure

- `frontend/` - Next.js app router app with Tailwind CSS and Google authentication
- `backend/` - FastAPI service for measurement responses and saved projects

## Environment

Copy the example files before running the apps:

- `frontend/.env.local.example` -> `frontend/.env.local`
- `backend/.env.example` -> `backend/.env`

Google OAuth setup for local development:

- In Google Cloud Console, open your OAuth 2.0 Client ID.
- Add Authorized JavaScript origin: `http://localhost:3000`
- Add Authorized redirect URI: `http://localhost:3000/api/auth/callback/google`
- Keep `NEXTAUTH_URL=http://localhost:3000` in `frontend/.env.local`

## Run locally

1. Install frontend dependencies inside `frontend/`.
2. Install backend dependencies inside `backend/`.
3. Start FastAPI on port `8000`.
4. Start Next.js on port `3000`.

Note: the current CV pipeline calibrates length and width from a reference width input, but height is still an estimate from 2D geometry. For truly accurate 3D height, add depth sensing or multi-view reconstruction.
