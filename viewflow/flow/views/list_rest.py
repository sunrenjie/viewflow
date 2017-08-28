from django.views import generic

from rest_framework import views as rest_views
from rest_framework.response import Response
from rest_framework import permissions

from viewflow.rest_views import APIViewWithoutCSRFEnforcement
from .list import TaskFilter, ProcessFilter

from ... import serializers

from ... import activation, models

from .mixins import (
    LoginRequiredMixin, FlowViewPermissionMixin,
    FlowListMixin
)


class AllProcessListRestView(LoginRequiredMixin, FlowListMixin, APIViewWithoutCSRFEnforcement):

    """All process instances list available for current user."""

    def get(self, request, *args, **kwargs):
        processes = [p for p in self.get_queryset()]
        return Response([serializers.ProcessSerializer(p).data for p in processes])

    def get_queryset(self):
        return models.Process.objects \
            .filter_available(self.flows, self.request.user) \
            .order_by('-created')


class AllTaskListRestView(FlowListMixin, APIViewWithoutCSRFEnforcement):

    def __init__(self, *args, **kwargs):
        self._filter = None
        super(AllTaskListRestView, self).__init__(*args, **kwargs)

    def get_permissions(self):
        perms = [permissions.IsAuthenticated()]
        return perms

    def get(self, request, *args, **kwargs):
        tasks = list(self.filter.qs)
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])

    @property
    def filter(self):
        if self._filter is None:
            self._filter = TaskFilter(self.request.GET, self.get_base_queryset(self.request.user))
        return self._filter

    def get_base_queryset(self, user):
        return models.Task.objects.inbox(self.flows, user).order_by('-created')


class AllQueueListRestView(FlowListMixin, APIViewWithoutCSRFEnforcement):

    def __init__(self, *args, **kwargs):
        self._filter = None
        super(AllQueueListRestView, self).__init__(*args, **kwargs)

    def get_queryset(self):
        return self.filter.qs

    @property
    def filter(self):
        if self._filter is None:
            self._filter = TaskFilter(self.request.GET, self.get_base_queryset(self.request.user))
        return self._filter

    def get_base_queryset(self, user):
        return models.Task.objects.queue(self.flows, user).order_by('-created')

    def get(self, request, *args, **kwargs):
        tasks = list(self.get_queryset())
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])


class AllArchiveListRestView(LoginRequiredMixin, FlowListMixin, APIViewWithoutCSRFEnforcement):

    """All tasks from all processes assigned to current user."""

    def get_queryset(self):
        return models.Task.objects.archive(self.flows, self.request.user).order_by('-created')

    def get(self, request, *args, **kwargs):
        tasks = list(self.get_queryset())
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])


class ProcessListRestView(FlowViewPermissionMixin, APIViewWithoutCSRFEnforcement):

    def __init__(self, **kwargs):
        self._filter = None
        super(ProcessListRestView, self).__init__(**kwargs)

    def get_queryset(self):
        return self.filter.qs

    @property
    def filter(self):
        if self._filter is None:
            self._filter = ProcessFilter(self.request.GET, self.get_base_queryset(self.request.user))
        return self._filter

    def get_base_queryset(self, user):
        return self.flow_class.process_class.objects \
            .filter(flow_class=self.flow_class) \
            .order_by('-created')

    def get(self, request, *args, **kwargs):
        processes = [p for p in self.filter.qs]
        return Response([serializers.ProcessSerializer(p).data for p in processes])


class TaskListRestView(FlowViewPermissionMixin, APIViewWithoutCSRFEnforcement):

    def get_queryset(self):
        return self.flow_class.task_class.objects \
            .filter(process__flow_class=self.flow_class,
                    owner=self.request.user,
                    status=activation.STATUS.ASSIGNED) \
            .order_by('-created')

    def get(self, request, *args, **kwargs):
        tasks = [t for t in self.get_queryset()]
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])


class QueueListRestView(FlowViewPermissionMixin, APIViewWithoutCSRFEnforcement):

    def get_queryset(self):
        queryset = self.flow_class.task_class.objects.user_queue(self.request.user, flow_class=self.flow_class) \
            .filter(status=activation.STATUS.NEW).order_by('-created')

        return queryset

    def get(self, request, *args, **kwargs):
        tasks = [t for t in self.get_queryset()]
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])


class ArchiveListRestView(FlowViewPermissionMixin, APIViewWithoutCSRFEnforcement):

    """All tasks from all processes assigned to current user."""

    def get_queryset(self):
        manager = self.flow_class.task_class._default_manager

        return manager.user_archive(
            self.request.user,
            flow_class=self.flow_class
        ).order_by('-created')

    def get(self, request, *args, **kwargs):
        tasks = [t for t in self.get_queryset()]
        return Response([serializers.TaskSerializer(task, request=request).data for task in tasks])
