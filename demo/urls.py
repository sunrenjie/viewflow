import django

from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views as auth
from rest_framework import routers

from viewflow.flow import views as viewflow

from .helloworld.flows import HelloWorldFlow
from .shipment.flows import ShipmentFlow
from .customnode.flows import DynamicSplitFlow
from .orderit.flows import OrderItCompleteProjectFlow

from viewflow.views import LoginView, LogoutView

if django.VERSION < (1, 7):
    admin.autodiscover()

flows = {
    'orderit': OrderItCompleteProjectFlow,
    'helloworld': HelloWorldFlow,
    'shipment': ShipmentFlow,
    'split': DynamicSplitFlow
}

router = routers.SimpleRouter()

urlpatterns = [
    url(r'^$', viewflow.AllProcessListView.as_view(ns_map=flows), name="index"),
    url('^api/v1/', include(router.urls)),
    url('^api/v1/auth/login/$', LoginView.as_view(), name='rest_login'),
    url('^api/v1/auth/logout/$', LogoutView.as_view(), name='rest_logout'),
    url('^api/v1/viewflow/tasks/$', viewflow.AllTaskListRestView.as_view(ns_map=flows), name='rest_viewflow_tasks'),
    url('^api/v1/viewflow/queue/$', viewflow.AllQueueListRestView.as_view(ns_map=flows), name='rest_viewflow_queue'),
    url(r'^tasks/$', viewflow.AllTaskListView.as_view(ns_map=flows), name="tasks"),
    url(r'^queue/$', viewflow.AllQueueListView.as_view(ns_map=flows), name="queue"),

    url(r'^helloworld/', include('demo.helloworld.urls', namespace='helloworld')),
    url(r'^shipment/', include('demo.shipment.urls', namespace='shipment')),
    url(r'^split/', include('demo.customnode.urls', namespace='split')),
    url(r'^orderit/', include('demo.orderit.urls', namespace='orderit')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/login/$', auth.login, name='login'),
    url(r'^accounts/logout/$', auth.logout, name='logout'),
    url(r'^', include('demo.website')),
]
