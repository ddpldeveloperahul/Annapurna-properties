import asyncio, json, logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import websockets
from integrations.elevenlabs.client import ElevenLabsClient
logger = logging.getLogger("anpurna_properties")

class ExotelVoiceBridgeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream_sid = None; self.call_sid = None; self.eleven_ws = None; self.eleven_reader = None
        await self.accept()
    async def disconnect(self, code):
        if self.eleven_reader: self.eleven_reader.cancel()
        if self.eleven_ws:
            try: await self.eleven_ws.close()
            except Exception: pass
    async def receive(self, text_data=None, bytes_data=None):
        if not text_data: return
        try: event = json.loads(text_data)
        except json.JSONDecodeError: return await self.close(code=1003)
        kind = event.get("event")
        if kind == "start":
            start = event.get("start", {}); self.stream_sid = start.get("stream_sid") or event.get("stream_sid"); self.call_sid = start.get("call_sid")
            await self._start_elevenlabs(); await self._record_stream_event("stream_started", event)
        elif kind == "media" and self.eleven_ws:
            payload = (event.get("media") or {}).get("payload")
            if payload: await self.eleven_ws.send(json.dumps({"user_audio_chunk": payload}))
        elif kind == "stop":
            await self._record_stream_event("stream_stopped", event); await self.close(code=1000)
    async def _start_elevenlabs(self):
        signed = await database_sync_to_async(ElevenLabsClient().get_signed_conversation_url)()
        self.eleven_ws = await websockets.connect(signed, max_size=2**22, ping_interval=15, ping_timeout=15)
        self.eleven_reader = asyncio.create_task(self._pump_elevenlabs())
    async def _pump_elevenlabs(self):
        try:
            async for raw in self.eleven_ws:
                msg = json.loads(raw); t = msg.get("type", "")
                if t == "conversation_initiation_metadata":
                    meta = msg.get("conversation_initiation_metadata_event") or {}
                    conversation_id = meta.get("conversation_id")
                    if conversation_id: await self._store_conversation_id(conversation_id)
                if t == "audio":
                    audio = (msg.get("audio_event") or {}).get("audio_base_64") or msg.get("audio")
                    if audio and self.stream_sid: await self.send(text_data=json.dumps({"event": "media", "stream_sid": self.stream_sid, "media": {"payload": audio}}))
                elif t in {"user_transcript", "agent_response", "user_message", "agent_response_event"}:
                    await self._record_stream_event("elevenlabs_" + t, msg)
                elif t in {"interruption", "interruption_event"} and self.stream_sid:
                    await self.send(text_data=json.dumps({"event": "clear", "stream_sid": self.stream_sid}))
        except asyncio.CancelledError: raise
        except Exception as exc:
            logger.exception("ElevenLabs bridge failed: %s", exc); await self._record_stream_event("voice_bridge_error", {"error": str(exc)}); await self.close(code=1011)
    @database_sync_to_async
    def _store_conversation_id(self, conversation_id):
        from myapp.models import Call
        if self.call_sid:
            Call.objects.filter(provider_call_sid=self.call_sid).update(voice_conversation_id=conversation_id)
    @database_sync_to_async
    def _record_stream_event(self, event_type, payload):
        from myapp.models import Call, CallEvent
        if not self.call_sid: return
        call = Call.objects.filter(provider_call_sid=self.call_sid).first()
        if call: CallEvent.objects.create(call=call, event_type=event_type, payload=payload)
