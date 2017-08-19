from django.views import generic
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from rest_framework import permissions, viewsets, status, views
from rest_framework import views as rest_views
from rest_framework.response import Response

from ... import serializers
from ...decorators import flow_view
from .mixins import FlowViewPermissionMixin


class DetailTaskRestView(rest_views.APIView):
    def __init__(self, **kwargs):
        self.activation = None
        super(DetailTaskRestView, self).__init__(**kwargs)

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        self.activation = request.activation

        if not self.activation.flow_task.can_view(request.user, self.activation.task):
            raise PermissionDenied
        return super(DetailTaskRestView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        raise RuntimeError("NA")


class DetailProcessRestView(FlowViewPermissionMixin, rest_views.APIView):

    def get_queryset(self):
        return self.flow_class.process_class._default_manager.all()

    def get(self, request, *args, **kwargs):
        pk = kwargs['process_pk']
        try:
            process = self.get_queryset().get(pk=pk)
            return Response(serializers.ProcessSerializer(process).data)
        except ObjectDoesNotExist:
            return Response({'message': "Process with the primary key '%s' does not exist." % pk},
                            status=status.HTTP_404_NOT_FOUND)
