from django.conf.urls import include, url
from django.conf.urls.static import static, settings
from django.views.generic import TemplateView
import views

urlpatterns = [
    url(r'^$', views.UserList.as_view(), name="select"),
    url(r'^upload/$', views.upload, name="upload"),
    url(r'^show/$', views.show, name="showuser"),
    url(r'^staypoints/$', views.stay, name="stay"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)