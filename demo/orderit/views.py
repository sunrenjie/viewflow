from datetime import datetime

from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory, inlineformset_factory
from django.utils.decorators import method_decorator
from django.views import generic
from django.shortcuts import render, redirect
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from viewflow.flow import flow_start_view
from viewflow.flow.views import FlowViewMixin, get_next_task_url

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from .models import Project, Order, OrderVM

from .serializers import OrderSerializer


class StartViewRest(GenericAPIView):
    serializer_class = OrderSerializer

    def __init__(self, **kwargs):
        super(StartViewRest, self).__init__(**kwargs)

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    def perform_create(self, serializer):
        # Injecting owner info into validated data.
        return serializer.save(owner=self.request.user)

    @classmethod
    def as_view(cls, **initkwargs):
        return super(StartViewRest, cls).as_view(**initkwargs)

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

start_view.rest_version = StartViewRest.as_view()


class OrderCompleteProjectView(FlowViewMixin, generic.UpdateView):
    def get_object(self):
        return self.activation.process.order
