# Production readiness

This backend now has live provider paths for Exotel outbound Voice AI calls, Exotel AgentStream WebSocket media, ElevenLabs signed Conversational AI WebSockets/transcript retrieval, OpenAI structured extraction/summaries, and Meta WhatsApp template sends/status webhooks.

## Required production configuration

- PostgreSQL and Redis/Celery.
- `AI_CALLING_MOCK_PROVIDERS=false`.
- Strong `DJANGO_SECRET_KEY` and explicit `DJANGO_ALLOWED_HOSTS`.
- Exotel SID/API key/token/caller ID, public WSS stream URL, and status callback URL. Configure Voicebot/AgentStream at 16 kHz to match the ElevenLabs agent audio format.
- ElevenLabs API key and private Agent ID. The WebSocket bridge obtains a server-side signed URL; never expose the API key.
- OpenAI API key and a model supporting Structured Outputs/Responses API.
- Meta WhatsApp phone-number ID/access token/app secret/verify token plus an approved template whose body variables match `_template_parameters()`.
- TLS termination that forwards `X-Forwarded-Proto=https`; WSS must be publicly reachable with a valid certificate.

## Before first migration

The lead mobile field is now globally unique to satisfy the SOW rule that a mobile number never creates two lead rows. If an existing database contains duplicate normalized mobile values, merge them before applying `leads.0002_strict_unique_mobile`.

## Provider setup

Exotel AgentStream/Voicebot should point to `wss://<host>/ws/telephony/exotel/stream/?sample-rate=16000`. Exotel sends `connected/start/media/stop` messages and the backend forwards PCM base64 media to ElevenLabs; ElevenLabs audio is returned to Exotel on the same socket.

Meta should use `/api/v1/whatsapp/webhooks/status/` for GET verification and POST status callbacks. POST callbacks are HMAC-verified with `WHATSAPP_APP_SECRET`.

## Operational checks

1. `python manage.py check --deploy`
2. `python manage.py migrate`
3. Start Daphne/ASGI and Celery worker.
4. Confirm Redis/PostgreSQL health.
5. Place a staging call and verify call -> voice conversation ID -> transcript -> lead -> summary -> follow-up -> WhatsApp.
6. Replay provider webhooks and confirm no duplicate event/lead/message.
7. Test WhatsApp `sent/delivered/read/failed` transitions.
8. Test caller hangup, AI/provider timeout, barge-in, invalid signatures and retry behavior.
