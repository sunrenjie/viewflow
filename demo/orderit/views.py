from datetime import datetime

import django
from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory, inlineformset_factory
from django.utils.decorators import method_decorator
from django.views import generic
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from viewflow.decorators import flow_view
from viewflow.flow import flow_start_view
from viewflow.flow.views import FlowViewMixin, get_next_task_url

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.exceptions import ValidationError

from viewflow.rest_views import GenericAPIViewWithoutCSRFEnforcement
from viewflow.serializers import TaskSerializer

from .models import Project, Order, OrderVM

from .serializers import OrderSerializer


class StartViewRest(GenericAPIViewWithoutCSRFEnforcement):
    serializer_class = OrderSerializer

    def __init__(self, **kwargs):
        super(StartViewRest, self).__init__(**kwargs)

    def initial(self, request, *args, **kwargs):
        # Because rest_framework.authentication.SessionAuthentication.authenticate() enforces CSRF check, which is
        # against REST API spirit, here we do its authentication job in advance so that CSRF check is disabled.
        user = request._request.user
        request.user = request._user = user
        return super(StartViewRest, self).initial(request, *args, **kwargs)

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    def perform_create(self, serializer):
        # Injecting owner info into validated data.
        return serializer.save(owner=self.request.user)

    @method_decorator(flow_start_view)
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # Cannot be implemented within get_permissions(), because at which time activation is not yet assigned to
        # request. Having to putting the validation here is a sacrifice of insisting on using flow_start_view.
        # Alternatively, we may put things from flow_start_view partly self.initial() and partly into this method
        # (in particular, the call to activation.lock.__exit__() is very important, without which the next task won't
        # be created at all). Then we will be able access request.activation in get_permissions().
        if not request.activation.has_perm(request.user):
            raise PermissionDenied

        # Behind activation (type: viewflow.flow.activation.ManagedStartViewActivation), there is a
        # viewflow.forms.ActivationDataForm, which is responsible for injecting a started datetime value (with
        # prefix "_viewflow_activation" into the form for the start page. Upon POST, that value is sent back and taken
        # as a protection against misusages. Here we simply prepare that form in data; for the mechanisms, see also
        # django.forms.fields.DateTimeField.to_python().
        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        # Contents of CreateModelMixin.create() copied here. We do the copy because we want to make use of the
        # serializer (for returning validated data) and created order object (for assigning to the process).
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.perform_create(serializer)

        request.process.order = order
        request.activation.done()
        return Response(serializer.data)


@flow_start_view
def start_view(request):
    form_class = modelform_factory(Project, fields=[
        'name',
    ], labels={'name': _('Project Name')})

    formset_class = inlineformset_factory(Project, OrderVM, fields=[
        'name', 'sockets', 'cores_per_socket', 'memory_GB', 'disks', 'nics'
    ])

    if not request.activation.has_perm(request.user):
        raise PermissionDenied

    request.activation.prepare(request.POST or None, user=request.user)

    form = form_class(request.POST or None)
    formset = formset_class(request.POST or None)

    is_valid = all([form.is_valid(), formset.is_valid()])
    if is_valid:
        project = form.save(commit=False)
        project.owner = request.user
        project.save()
        request.process.project = project
        order = Order(project=project)
        order.save()
        request.process.order = order
        for item in formset.save(commit=False):
            item.project = project
            item.order = order
            item.save()

        request.activation.done()
        return redirect(get_next_task_url(request, request.process))
    return render(request, 'orderit/complete_project_start.html', {
        'activation': request.activation,
        'form': form,
        'formset': formset,
    })

start_view.REST_VERSION = StartViewRest


class OrderCompleteProjectRestView(GenericAPIViewWithoutCSRFEnforcement, FlowViewMixin):
    fields = None
    serializer_class = OrderSerializer
    task_serializer_class = TaskSerializer

    def __init__(self, **kwargs):
        self.activation = None
        super(OrderCompleteProjectRestView, self).__init__(**kwargs)

    def get_object(self, queryset=None):
        return self.activation.process.order

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        if not self.activation.prepare.can_proceed():
            raise ValidationError('The task cannot be executed.')

        if not self.activation.has_perm(request.user):
            raise PermissionDenied

        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        # save business logic object data
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
        msg = 'The task has been completed successfully.'
        # Don't try to report that the process is finished or not here. Because that seems not working.

        return Response({'message': msg})

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj_data = self.get_serializer(obj).data
        task = self.activation.task
        task_data = self.task_serializer_class(task).data
        return Response({'object': obj_data, 'task': task_data})

    @method_decorator(flow_view)
    def dispatch(self, request, **kwargs):
        self.activation = request.activation
        return super(OrderCompleteProjectRestView, self).dispatch(request, **kwargs)

    @classmethod
    def as_view(cls, **initkwargs):
        return super(OrderCompleteProjectRestView, cls).as_view(**initkwargs)


class OrderCompleteProjectView(FlowViewMixin, generic.UpdateView):
    REST_VERSION = OrderCompleteProjectRestView

    def get_object(self, queryset=None):
        return self.activation.process.order
