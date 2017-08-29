from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory, inlineformset_factory
from django.views import generic
from django.shortcuts import render, redirect

from demo.shipment.serializers import ShipmentSerializer, InsuranceSerializer
from viewflow.flow import flow_start_view
from viewflow.flow.views import FlowViewMixin, get_next_task_url
from viewflow.rest_views import StartViewRest, FinishAssignedTaskWithFieldsRestView

from .models import Shipment, ShipmentItem, Insurance


class ShipmentStartRestView(StartViewRest):
    serializer_class = ShipmentSerializer
    object_field_name = 'shipment'


@flow_start_view
def start_view(request):
    form_class = modelform_factory(Shipment, fields=[
        'shipment_no', 'first_name', 'last_name',
        'email', 'phone', 'address', 'zipcode',
        'city', 'state', 'country'])

    formset_class = inlineformset_factory(Shipment, ShipmentItem, fields=[
        'name', 'quantity'], can_delete=False)

    if not request.activation.has_perm(request.user):
        raise PermissionDenied
    request.activation.prepare(request.POST or None, user=request.user)

    form = form_class(request.POST or None)
    formset = formset_class(request.POST or None)

    is_valid = all([form.is_valid(), formset.is_valid()])
    if is_valid:
        shipment = form.save()
        request.process.shipment = shipment
        for item in formset.save(commit=False):
            item.shipment = shipment
            item.save()
        request.activation.done()
        return redirect(get_next_task_url(request, request.process))

    return render(request, 'shipment/shipment/start.html', {
        'activation': request.activation,
        'form': form,
        'formset': formset
    })

start_view.REST_VERSION = ShipmentStartRestView


class ShipmentRestView(FinishAssignedTaskWithFieldsRestView):
    serializer_class = ShipmentSerializer

    def get_object(self, queryset=None):
        return self.activation.process.shipment


class ShipmentView(FlowViewMixin, generic.UpdateView):
    REST_VERSION = ShipmentRestView

    def get_object(self):
        return self.activation.process.shipment


class InsuranceRestView(FinishAssignedTaskWithFieldsRestView):
    serializer_class = InsuranceSerializer
    fields = ['company_name', 'cost']

    def get_object(self, queyset=None):
        return Insurance()

    def activation_done(self, activation, obj):
        shipment = activation.process.shipment
        shipment.insurance = obj
        shipment.save()
        super(InsuranceRestView, self).activation_done(activation, obj)


class InsuranceView(FlowViewMixin, generic.CreateView):
    REST_VERSION = InsuranceRestView
    model = Insurance
    fields = ['company_name', 'cost']

    def activation_done(self, form):
        shipment = self.activation.process.shipment
        shipment.insurance = self.object
        shipment.save(update_fields=['insurance'])
        self.activation.done()
