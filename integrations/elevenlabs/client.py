import logging
import requests
from django.conf import settings

logger=logging.getLogger("anpurna_properties")
MOCK_TRANSCRIPT=[
 {"speaker":"AI","text":"Namaste! Main AI assistant hoon. Aap buy, sell ya rent ke liye enquiry kar rahe hain?"},
 {"speaker":"Customer","text":"Main Whitefield mein apartment khareedna chahta hoon, budget 70 se 90 lakh hai."},
]
class ElevenLabsError(Exception): pass
class ElevenLabsClient:
    def __init__(self):
        self.mock=settings.AI_CALLING_MOCK_PROVIDERS; self.api_key=settings.ELEVENLABS_API_KEY
        self.base=settings.ELEVENLABS_API_BASE_URL.rstrip('/'); self.timeout=settings.PROVIDER_HTTP_TIMEOUT_SECONDS
    @property
    def headers(self): return {"xi-api-key":self.api_key,"Accept":"application/json"}
    def get_signed_conversation_url(self):
        if self.mock: return "wss://mock-elevenlabs.invalid/conversation"
        try:
            r=requests.get(f"{self.base}/v1/convai/conversation/get-signed-url", params={"agent_id":settings.ELEVENLABS_AGENT_ID}, headers=self.headers, timeout=self.timeout)
            r.raise_for_status(); return r.json()["signed_url"]
        except (requests.RequestException,KeyError) as exc: raise ElevenLabsError(f"Unable to obtain ElevenLabs signed URL: {exc}") from exc
    def fetch_conversation_transcript(self, conversation_id):
        if self.mock: return MOCK_TRANSCRIPT
        try:
            r=requests.get(f"{self.base}/v1/convai/conversations/{conversation_id}",headers=self.headers,timeout=self.timeout); r.raise_for_status(); data=r.json()
        except requests.RequestException as exc: raise ElevenLabsError(f"Transcript fetch failed: {exc}") from exc
        turns=[]
        for item in data.get("transcript",[]):
            role=(item.get("role") or "").lower(); text=item.get("message") or item.get("text") or ""
            if text: turns.append({"speaker":"Customer" if role in {"user","customer"} else "AI","text":text})
        return turns
