import logging
import uuid
import requests
from django.conf import settings

logger = logging.getLogger("anpurna_properties")

class ExotelError(Exception):
    pass

class ExotelClient:
    def __init__(self):
        self.sid=settings.EXOTEL_SID; self.api_key=settings.EXOTEL_API_KEY; self.api_token=settings.EXOTEL_API_TOKEN
        self.caller_id=settings.EXOTEL_CALLER_ID; self.mock=settings.AI_CALLING_MOCK_PROVIDERS
        self.base=settings.EXOTEL_API_BASE_URL.rstrip("/"); self.timeout=settings.PROVIDER_HTTP_TIMEOUT_SECONDS

    def _request(self, method, path, **kwargs):
        try:
            r=requests.request(method, self.base+path, auth=(self.api_key,self.api_token), timeout=self.timeout, **kwargs)
            r.raise_for_status(); return r
        except requests.RequestException as exc:
            raise ExotelError(f"Exotel request failed: {exc}") from exc

    def fetch_call_details(self, call_sid):
        if self.mock: return {"sid":call_sid,"recordingurl":f"https://mock-exotel-recordings.example.com/{call_sid}.mp3"}
        r=self._request("GET", f"/v1/Accounts/{self.sid}/Calls/{call_sid}.json")
        data=r.json(); return data.get("Call") or data.get("call") or data

    def fetch_recording_url(self, call_sid):
        d=self.fetch_call_details(call_sid)
        return d.get("RecordingUrl") or d.get("recordingurl") or d.get("recording_url") or ""

    def originate_callback(self, to_number, from_number=None):
        if self.mock: return {"call_sid":f"mock-{uuid.uuid4().hex[:12]}","status":"queued"}
        payload={"from":to_number,"callerid":from_number or self.caller_id,"streamurl":settings.EXOTEL_STREAM_URL,"streamtype":"bidirectional","record":"true"}
        if settings.EXOTEL_STATUS_CALLBACK_URL:
            payload["statuscallback"]=settings.EXOTEL_STATUS_CALLBACK_URL
            payload["statuscallbackevents[]"]="terminal"
        r=self._request("POST", f"/v1/accounts/{self.sid}/calls/connect", files={k:(None,str(v)) for k,v in payload.items()})
        data=r.json().get("call", r.json())
        return {"call_sid":data.get("sid"),"status":data.get("status","queued"),"raw":data}
