from django.urls import path

from icat_cbs import views

urlpatterns = [path("topic/<topic>", views.agent_callback)]
