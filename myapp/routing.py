from django.urls import re_path
from .consumers import ExotelVoiceBridgeConsumer
websocket_urlpatterns=[re_path(r"^ws/telephony/exotel/stream/$",ExotelVoiceBridgeConsumer.as_asgi())]
