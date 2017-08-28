from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch
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

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        self.server_prefix = request.build_absolute_uri('/')[:-1].strip("/") if request else ''
        super(TaskSerializer, self).__init__(*args, **kwargs)

    def to_representation(self, instance):
        data = super(TaskSerializer, self).to_representation(instance)
        links = {}
        for t in ['', 'assign']:
            url = instance.get_url(url_type=t)
            if url:
                links[t] = self.server_prefix + url
        data['links'] = links
        return data
