
from django.contrib.auth import models as dj_models

from rest_framework import serializers

from . import models as models


class AccountSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True, required=False)
    phone = serializers.ReadOnlyField(source='profile.phone')
    more_info = serializers.ReadOnlyField(source='profile.more_info')

    class Meta:
        model = dj_models.User
        fields = ('email', 'username', 'password', 'confirm_password', 'phone', 'more_info')


class ProcessSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='flow_class.process_title')

    class Meta:
        model = models.Process
        fields = ('id', 'title', 'status', 'created', 'finished')


class TaskSerializer(serializers.ModelSerializer):
    process = ProcessSerializer()
    task_name = serializers.CharField(source='flow_task.name')
    process_summary = serializers.CharField(source='flow_process.summary')
    task_description = serializers.CharField(source='summary')

    class Meta:
        model = models.Task
        fields = ('id', 'owner', 'process', 'process_summary', 'task_name', 'task_description', 'status', 'created',
                  'started', 'finished', 'comments')
