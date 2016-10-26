from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory, inlineformset_factory
from django.views import generic
from django.shortcuts import render, redirect

from django.utils.translation import ugettext_lazy as _

from viewflow.flow import flow_start_view
from viewflow.flow.views import FlowViewMixin, get_next_task_url

from rest_framework import permissions, viewsets
from rest_framework import status
from rest_framework.response import Response

from .models import Project, Order, OrderVM
from .permissions import IsOwnerOfProject, IsSuperPowerfulUser, IsOwnerOfOrder


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


class OrderCompleteProjectView(FlowViewMixin, generic.UpdateView):
    def get_object(self):
        return self.activation.process.order

