from django.urls import path

from icat_cbs import views

urlpatterns = [path("<topic>", views.agent_callback)]
