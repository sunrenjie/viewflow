from django.conf.urls import url, include

from .views import list_rest, detail_rest


class FlowViewSet(object):
    """
    Shortcut for flow urls routing

    Usage::

        urlpatterns = [
            url(r'/helloworld/', FlowViewSet(HelloWorldFlow).urls)
        ]
    """

    process_list_view = [
        r'^$',
        list_rest.ProcessListRestView.as_view(),
        'index'
    ]

    detail_process_view = [
        r'^(?P<process_pk>\d+)/$',
        detail_rest.DetailProcessRestView.as_view(),
        'detail'
    ]

    # TODO cancel_process_view is temporarily removed.

    queue_list_view = [
        '^queue/$',
        list_rest.QueueListRestView.as_view(),
        'queue',
    ]

    archive_list_view = [
        '^archive/$',
        list_rest.ArchiveListRestView.as_view(),
        'archive',
    ]

    inbox_list_view = [
        '^tasks/$',
        list_rest.TaskListRestView.as_view(),
        'tasks'
    ]

    def __init__(self, flow_class):
        self.flow_class = flow_class

    def create_url_entry(self, url_entry):
        regexp, view, name = url_entry
        return url(regexp, view, name=name)

    def get_list_urls(self):
        attrs = (getattr(self, attr) for attr in dir(self) if attr.endswith('_view'))
        return [
            self.create_url_entry(value)
            for value in attrs if isinstance(value, (list, tuple))
        ]

    @property
    def urls(self):
        return [
            url('', include(self.get_list_urls()), {'flow_class': self.flow_class}),
            self.flow_class.instance.urls
        ]
