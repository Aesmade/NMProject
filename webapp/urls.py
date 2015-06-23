from django.conf.urls import include, url
from django.conf.urls.static import static, settings
import views

urlpatterns = [
    url(r'^$', views.index),
    url(r'^upload/$', views.upload),
    url(r'^select/$', views.UserList.as_view()),
    url(r'^show/$', views.show, name="showuser"),
    url(r'^staypoints/$', views.stay, name="stay"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)