import django
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.views import generic
from django.utils.decorators import method_decorator

from rest_framework import permissions
from rest_framework.exceptions import ValidationError

from datetime import datetime

from rest_framework.response import Response

from ...rest_views import APIViewWithoutCSRFEnforcement
from ...decorators import flow_start_view
from .mixins import MessageUserMixin
from .utils import get_next_task_url


class BaseStartFlowMixin(object):

    """Mixin for start views, that do not implement activation interface."""

    def get_context_data(self, **kwargs):
        """Add ``activation`` to context data."""
        kwargs['activation'] = self.activation
        return super(BaseStartFlowMixin, self).get_context_data(**kwargs)

    def get_success_url(self):
        return get_next_task_url(self.request, self.activation.process)

    def get_template_names(self):
        flow_task = self.activation.flow_task
        opts = self.activation.flow_task.flow_class._meta

        return (
            '{}/{}/{}.html'.format(opts.app_label, opts.flow_label, flow_task.name),
            '{}/{}/start.html'.format(opts.app_label, opts.flow_label),
            'viewflow/flow/start.html')

    @method_decorator(flow_start_view)
    def dispatch(self, request, **kwargs):
        """Check user permissions, and prepare flow to execution."""
        self.activation = request.activation
        if not self.activation.has_perm(request.user):
            raise PermissionDenied

        self.activation.prepare(request.POST or None, user=request.user)
        return super(BaseStartFlowMixin, self).dispatch(request, **kwargs)


class StartFlowMixin(MessageUserMixin, BaseStartFlowMixin):
    def activation_done(self, *args, **kwargs):
        """Finish activation."""
        self.activation.done()
        self.success('Process {process} has been started.')

    def form_valid(self, *args, **kwargs):
        super(StartFlowMixin, self).form_valid(*args, **kwargs)
        self.activation_done(*args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())


class CreateProcessRestView(APIViewWithoutCSRFEnforcement):
    fields = None  # required for it to accept fields arguments, yet be able to get through as_view() safely.

    def __init__(self, **kwargs):
        super(CreateProcessRestView, self).__init__(**kwargs)
        if self.fields is None:
            self.fields = []
        self.activation = None

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    @method_decorator(flow_start_view)
    def dispatch(self, request, **kwargs):
        """Check user permissions, and prepare flow to execution."""
        self.activation = request.activation
        return super(CreateProcessRestView, self).dispatch(request, 'foo', 'bar', **kwargs)

    @property
    def model(self):
        return self.activation.flow_class.process_class

    def get_object(self, queyset=None):
        return self.activation.process

    def get(self, request, *args, **kwargs):
        raise PermissionDenied

    def post(self, request, *args, **kwargs):
        if not self.activation.has_perm(request.user):
            raise PermissionDenied
        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        obj = self.get_object()
        for attr, value in request.data.items():
            if attr not in self.fields:
                raise ValidationError("'%s' is not one of the attributes this task is designed to change. "
                                      "Allowed attributes are %s." % (attr, str(self.fields)))
            setattr(obj, attr, value)
        try:
            obj.save()
        except django.core.exceptions.ValidationError as e:
            # Translate the django version of exception to a Rest Framework version, so that the Rest Framework may
            # do the rest of work.
            raise ValidationError({'messages': e.messages})

        self.activation.done()
        return Response({'message': 'A new process (id=%s) is started.' % str(obj.id)})

    @classmethod
    def as_view(cls, **initkwargs):
        return super(CreateProcessRestView, cls).as_view(**initkwargs)


class CreateProcessView(StartFlowMixin, generic.UpdateView):
    REST_VERSION = CreateProcessRestView

    def __init__(self, *args, **kwargs):
        super(CreateProcessView, self).__init__(**kwargs)
        if self.form_class is None and self.fields is None:
            self.fields = []

    @property
    def model(self):
        return self.activation.flow_class.process_class

    def get_object(self, queyset=None):
        return self.activation.process
