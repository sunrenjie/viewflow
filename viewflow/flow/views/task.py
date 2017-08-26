from django.utils.six.moves.urllib.parse import quote as urlquote

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views import generic
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.views.decorators.csrf import csrf_exempt

from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status, permissions

from viewflow.rest_views import APIViewWithoutCSRFEnforcement, GenericAPIViewWithoutCSRFEnforcement
from ...decorators import flow_view
from .actions import BaseTaskActionView
from .mixins import MessageUserMixin
from .utils import get_next_task_url


class BaseFlowViewMixin(object):
    """
    Mixin for task views, that do not implement activation interface.
    """

    def get_context_data(self, **kwargs):
        context = super(BaseFlowViewMixin, self).get_context_data(**kwargs)
        context['activation'] = self.activation
        return context

    def get_success_url(self):
        return get_next_task_url(self.request, self.activation.process)

    def get_template_names(self):
        flow_task = self.activation.flow_task
        opts = self.activation.flow_task.flow_class._meta

        return (
            '{}/{}/{}.html'.format(opts.app_label, opts.flow_label, flow_task.name),
            '{}/{}/task.html'.format(opts.app_label, opts.flow_label),
            'viewflow/flow/task.html')

    @method_decorator(flow_view)
    def dispatch(self, request, **kwargs):
        self.activation = request.activation

        if not self.activation.prepare.can_proceed():
            self.error('Task {task} cannot be executed.')
            return redirect(self.activation.flow_task.get_task_url(
                self.activation.task, url_type='detail', user=request.user,
                namespace=self.request.resolver_match.namespace))

        if not self.activation.has_perm(request.user):
            raise PermissionDenied

        self.activation.prepare(request.POST or None)
        return super(BaseFlowViewMixin, self).dispatch(request, **kwargs)


class FlowViewMixin(MessageUserMixin, BaseFlowViewMixin):
    def activation_done(self, *args, **kwargs):
        """Finish activation."""
        self.activation.done()
        self.success('Task {task} has been completed.')
        if self.activation.process.finished:
            self.success('Process {process} has been completed.')

    def form_valid(self, *args, **kwargs):
        super(FlowViewMixin, self).form_valid(*args, **kwargs)
        self.activation_done(*args, **kwargs)
        return HttpResponseRedirect(self.get_success_url())

# FIXME The rest views UpdateProcessRestView and AssignTaskRestView cannot be moved out of this file.
# They are referenced by their 'traditional' counterparts as "REST_VERSION", yet they need FlowViewMixin as base class.
# Such cyclic reference can only be resolved by a larger scale of refactoring; we'd hate to do that.


class UpdateProcessRestView(GenericAPIViewWithoutCSRFEnforcement, FlowViewMixin, generic.UpdateView):
    # TODO used in helloworld demo app; implement it.
    def post(self, request, *args, **kwargs):
        raise NotImplementedError


class UpdateProcessView(FlowViewMixin, generic.UpdateView):
    REST_VERSION = UpdateProcessRestView

    def __init__(self, *args, **kwargs):
        super(UpdateProcessView, self).__init__(*args, **kwargs)
        if self.form_class is None and self.fields is None:
            self.fields = []

    @property
    def model(self):
        return self.activation.flow_class.process_class

    def get_object(self, queryset=None):
        return self.activation.process


class AssignTaskRestView(APIViewWithoutCSRFEnforcement):

    def get_permissions(self):
        perms = [permissions.IsAuthenticated()]
        return perms

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        namespace = self.request.resolver_match.namespace
        task_detail_url = self.activation.task.flow_task.get_task_url(
            self.activation.task, url_type='detail', user=self.request.user, namespace=namespace)

        if not self.activation.assign.can_proceed():
            return Response({'message': "The task is in '%s' status and cannot be assigned." %
                                        self.activation.task.status}, status=status.HTTP_409_CONFLICT)

        if not self.activation.flow_task.can_assign(request.user, self.activation.task):
            return Response({'message': 'The task cannot be assigned to you.'}, status=status.HTTP_403_FORBIDDEN)

        self.activation.assign(self.request.user)
        return Response({'messsage': 'Task has been assigned to you successfully.',
                         'link': {
                             'detail': task_detail_url
                         }})

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        self.activation = request.activation
        # The calls to can_proceed() and can_assign() have to be performed in post(), since at that point, we are
        # called by rest_framework.views.dispatch(), where proper work is done such that we could return a
        # rest_framework.response.Response object. Making the calls here will result in error.

        return super(AssignTaskRestView, self).dispatch(request, *args, **kwargs)


class AssignTaskView(MessageUserMixin, generic.TemplateView):
    """
    Default assign view for flow task.

    Get confirmation from user, assigns task and redirects to task pages
    """

    REST_VERSION = AssignTaskRestView

    def get_template_names(self):
        flow_task = self.activation.flow_task
        opts = self.activation.flow_class._meta

        return (
            '{}/{}/{}_assign.html'.format(opts.app_label, opts.flow_label, flow_task.name),
            '{}/{}/task_assign.html'.format(opts.app_label, opts.flow_label),
            'viewflow/flow/task_assign.html')

    def get_context_data(self, **kwargs):
        context = super(AssignTaskView, self).get_context_data(**kwargs)
        context['activation'] = self.activation
        return context

    def get_success_url(self):
        """Continue on task or redirect back to task list."""
        url = self.activation.flow_task.get_task_url(
            self.activation.task, url_type='guess', user=self.request.user,
            namespace=self.request.resolver_match.namespace)

        back = self.request.GET.get('back', None)
        if back and not is_safe_url(url=back, host=self.request.get_host()):
            back = '/'

        if '_continue' in self.request.POST and back:
            url = "{}?back={}".format(url, urlquote(back))
        elif back:
            url = back

        return url

    def post(self, request, *args, **kwargs):
        if '_assign' or '_continue' in request.POST:
            self.activation.assign(self.request.user)
            self.success('Task {task} has been assigned')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.get(request, *args, **kwargs)

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        self.activation = request.activation

        if request.user is None or request.user.is_anonymous():
            raise PermissionDenied

        if not self.activation.assign.can_proceed():
            self.error('Task {task} cannot be assigned to you')
            return redirect(self.activation.flow_task.get_task_url(
                self.activation.task, url_type='detail', user=request.user,
                namespace=self.request.resolver_match.namespace))

        if not self.activation.flow_task.can_assign(request.user, self.activation.task):
            raise PermissionDenied

        return super(AssignTaskView, self).dispatch(request, *args, **kwargs)


class UnassignTaskRestView(APIViewWithoutCSRFEnforcement):
    pass  # TODO implement it.


class UnassignTaskView(BaseTaskActionView):
    REST_VERSION = UnassignTaskRestView
    action_name = 'unassign'

    def can_proceed(self):
        if self.activation.unassign.can_proceed():
            return self.activation.flow_task.can_unassign(self.request.user, self.activation.task)
        return False

    def perform(self):
        self.activation.unassign()
        self.success('Task {task} has been unassigned.')
