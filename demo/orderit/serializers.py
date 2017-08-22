from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from . import models as models


class ProjectSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        project, _ = models.Project.objects.get_or_create(**validated_data)

    class Meta:
        model = models.Project
        fields = ('id', 'owner', 'name')
        read_only_fields = ('id', 'owner')


class OrderVMSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OrderVM
        fields = ('id', 'name', 'sockets', 'cores_per_socket', 'memory_GB', 'disks', 'nics')
        read_only_fields = ('id',)


class OrderSerializer(serializers.ModelSerializer):
    project = ProjectSerializer()
    VMs = OrderVMSerializer(many=True, required=True)

    def create(self, validated_data):
        VMs_data = validated_data.pop('VMs')
        project_data = validated_data.pop('project')
        owner = validated_data.pop('owner')

        if list(models.Project.objects.filter(owner=owner, **project_data)):
            raise ValidationError('The project already exists')

        # pre-mature checking of VM name duplication
        vm_names = [vm['name'] for vm in VMs_data]
        if len(vm_names) != len(set(vm_names)):
            raise ValidationError('The VM list contains duplicated name')

        project = models.Project.objects.create(owner=owner, **project_data)
        order = models.Order.objects.create(project=project, is_active=True, **validated_data)
        for data in VMs_data:
            vm = models.OrderVM.objects.create(project=project, order=order, **data)
        return order

    class Meta:
        model = models.Order
        fields = ('id', 'project', 'is_active', 'created_at', 'updated_at', 'VMs')
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_active')
