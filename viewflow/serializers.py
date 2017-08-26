from django.contrib.auth import get_user_model
from rest_framework import serializers

from . import models as models

user_model = get_user_model()


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_model
        fields = ('email', 'username')


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
