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

from viewflow.rest_views import LoginRestView, LogoutRestView
from viewflow.flow.views import list_rest

if django.VERSION < (1, 7):
    admin.autodiscover()

flows = {
    'helloworld': HelloWorldFlow,
    'shipment': ShipmentFlow,
    'split': DynamicSplitFlow,
    'orderit': OrderItCompleteProjectFlow,
}

router = routers.SimpleRouter()

urlpatterns = [
    url(r'^$', viewflow.AllProcessListView.as_view(ns_map=flows), name="index"),
    url('^api/v1/', include(router.urls)),
    url('^api/v1/auth/login/$', LoginRestView.as_view(), name='rest_login'),
    url('^api/v1/auth/logout/$', LogoutRestView.as_view(), name='rest_logout'),
    url('^api/v1/viewflow/tasks/$', list_rest.AllTaskListRestView.as_view(ns_map=flows), name='rest_viewflow_tasks'),
    url('^api/v1/viewflow/queue/$', list_rest.AllQueueListRestView.as_view(ns_map=flows), name='rest_viewflow_queue'),

    # Note that the namespace for the per-app REST API URL shall be of the format 'rest_viewflow_app_xxx', where 'xxx'
    # is the name of the app. It is critical for reversing from view name to URL. See also
    # viewflow.models.AbstractTask.get_url().
    url('^api/v1/viewflow/helloworld/', include('demo.helloworld.urls_rest', namespace='rest_viewflow_app_helloworld')),
    url('^api/v1/viewflow/shipment/', include('demo.shipment.urls_rest', namespace='rest_viewflow_app_shipment')),
    url('^api/v1/viewflow/split/', include('demo.customnode.urls_rest', namespace='rest_viewflow_app_split')),
    url('^api/v1/viewflow/orderit/', include('demo.orderit.urls_rest', namespace='rest_viewflow_app_orderit')),
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
