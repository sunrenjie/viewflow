from django.views import generic
from django.http import HttpResponseRedirect

from viewflow.flow.views import FlowViewMixin
from viewflow.rest_views import FinishAssignedTaskWithFieldsRestView

from . import models


class DecisionRestView(FinishAssignedTaskWithFieldsRestView):
    fields = ['decision']

    def get_object(self, queyset=None):
        obj, _ = models.Decision.objects.get_or_create(user=self.request.user, process=self.activation.process)
        return obj


class DecisionView(FlowViewMixin, generic.CreateView):
    REST_VERSION = DecisionRestView
    model = models.Decision
    fields = ['decision']

    def form_valid(self, form):
        self.object = form.save(commit=False)

        self.object.user = self.request.user
        self.object.process = self.activation.process
        self.object.save()

        self.activation.done()
        self.success('Task {task} has been completed.')

        return HttpResponseRedirect(self.get_success_url())
