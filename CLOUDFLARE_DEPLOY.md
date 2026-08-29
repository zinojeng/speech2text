# Cloudflare Containers deployment

This repository keeps its existing Streamlit Docker image and exposes it through
a Cloudflare Worker backed by a single Container instance.

## Cloudflare configuration

- Worker name: `speech2text`
- Container port: `8080`
- Instance type: `standard-1` (4 GiB RAM, 8 GB disk)
- Maximum instances: `1`
- Idle shutdown: `10m`
- Production deploy command: `npx wrangler deploy`

The following values must be stored as Cloudflare Worker secrets, never as plain
text variables or committed files:

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY` when ElevenLabs transcription is used

The container filesystem is ephemeral. Uploaded and generated files disappear
when the instance sleeps or is replaced during a deployment.
