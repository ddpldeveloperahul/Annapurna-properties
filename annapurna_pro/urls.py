from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from myapp.views import home_view

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", home_view, name="login"),
    path("signup/", home_view, name="signup"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("myapp.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]


