import logging, random, uuid, requests
from django.conf import settings
logger=logging.getLogger("anpurna_properties")
class WhatsAppSendError(Exception): pass
class WhatsAppClient:
    def __init__(self):
        self.phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID; self.access_token=settings.WHATSAPP_ACCESS_TOKEN
        self.mock=settings.AI_CALLING_MOCK_PROVIDERS; self.timeout=settings.PROVIDER_HTTP_TIMEOUT_SECONDS
    def send_template(self,to_number,template_name,language,body_preview="",parameters=None):
        if self.mock:
            if random.random()<0.08: raise WhatsAppSendError("Recipient number not on WhatsApp")
            return {"message_id":f"wamock.{uuid.uuid4().hex[:16]}"}
        url=f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/{self.phone_number_id}/messages"
        components=[]
        if parameters:
            components=[{"type":"body","parameters":[{"type":"text","text":str(x)} for x in parameters]}]
        payload={"messaging_product":"whatsapp","to":to_number.lstrip('+'),"type":"template","template":{"name":template_name,"language":{"code":language}}}
        if components: payload["template"]["components"]=components
        try:
            r=requests.post(url,json=payload,headers={"Authorization":f"Bearer {self.access_token}","Content-Type":"application/json"},timeout=self.timeout); r.raise_for_status(); data=r.json()
            return {"message_id":data["messages"][0]["id"],"raw":data}
        except (requests.RequestException,KeyError,IndexError) as exc:
            detail=getattr(getattr(exc,"response",None),"text",str(exc)); raise WhatsAppSendError(f"WhatsApp send failed: {detail[:500]}") from exc
