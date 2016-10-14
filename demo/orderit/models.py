import uuid
import re
from datetime import datetime

from django.contrib.auth.models import User
from django.db import models, IntegrityError

from viewflow.models import Process, Task


def generate_uuid_hex():
    return uuid.uuid4().hex


def generate_random_with_full_datetime_prefix():
    return datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[0:4]


def generate_random_order_id_with_full_datetime_prefix():
    return 'order-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[0:4]


def generate_random_vm_id_with_full_datetime_prefix():
    return 'vm-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[0:4]


def is_valid_uuid_hex(s):
    return bool(s and re.match('^[a-f0-9]{1,32}$', s))


class Project(models.Model):
    # NOTICE for dummies: editable=False means having default way of generating it; when creating a new object via
    # POST, such columns will not be included. Only one first is special, as it is already from session.
    id = models.CharField(max_length=36, primary_key=True,
                          default=generate_uuid_hex, editable=False)
    owner = models.ForeignKey(User, editable=False)
    name = models.CharField(max_length=32)

    class Meta:
        unique_together= (('owner', 'name'), )  # only uniqueness in the owner's universe


class Order(models.Model):
    # Orders explicitly encourage amendments, the history can be stored in form of serialized json.
    # Our model design principle here: at least leave one unique field with editable=True. Columns with editable=False
    # will not have its data collected from POST'ed json data. If no unique field appears there, we cannot tell
    # whether the object POST'ed by the user is an existing one.
    id = models.CharField(max_length=26, primary_key=True, editable=False,
                          default=generate_random_order_id_with_full_datetime_prefix)
    project = models.ForeignKey(Project)
    is_active = models.BooleanField(default=True)

    vms_amended = models.BooleanField(default=False)
    vms_request_for_review = models.BooleanField(default=False)
    vms_verified = models.BooleanField(default=False)
    vms_confirmed = models.BooleanField(default=False)
    vms_deployed = models.BooleanField(default=False)
    vms_software_installed = models.BooleanField(default=False)

    security_fixed = models.BooleanField(default=False)
    security_confirmed = models.BooleanField(default=False)

    external_ip = models.CharField(max_length=1024)  # separated by ';'
    external_ip_confirmed = models.BooleanField(default=False)
    external_ip_deployed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)


class OrderVM(models.Model):
    # Redundant 'project' entry added to ensure uniqueness of (project-name, vm-name)
    # TODO come up with a better technique to avoid the awkward redundancy.
    id = models.CharField(max_length=23, primary_key=True, editable=False,
                          default=generate_random_vm_id_with_full_datetime_prefix)
    project = models.ForeignKey(Project, editable=False)  # auto-assigned at save()
    order = models.ForeignKey(Order, related_name='VMs')  # for handling together in API
    name = models.CharField(max_length=16)
    sockets = models.IntegerField()
    cores_per_socket = models.IntegerField()
    memory_GB = models.IntegerField()
    disks = models.CharField(max_length=32)  # real numbers (of disk size; GB) separated by ';'
    nics = models.CharField(max_length=1024)  # separated by ';'

    class Meta:
        unique_together= (('project', 'name'), )

    def save(self, *args, **kargs):
        self.project = self.order.project
        return super(OrderVM, self).save(*args, **kargs)


class OrderItCompleteProjectProcess(Process):
    order = models.ForeignKey(Order, blank=True, null=True)

    def is_security_clear(self):
        try:
            if self.order.security_fixed and self.order.security_confirmed:
                return True
            else:
                return False
        except Order.DoesNotExist:
            return False

    def is_external_ip_confirmed(self):
        try:
            return True if self.order.external_ip and self.order.external_ip_confirmed else False
        except Order.DoesNotExist:
            return False

    class Meta:
        verbose_name_plural = 'Order complete project process list'
        permissions = [
            ('can_start_order', 'Can initiate an order process'),
            ('can_verify_order', 'Can verify that an order is technically possible'),
            ('can_confirm_order', 'Can confirm an order'),
            ('can_deploy_virtual_machines', 'Can deploy virtual machines'),
            ('can_confirm_security_status', 'Can confirm that the VMs are secure according to security scan'),
            ('can_confirm_external_ip', 'Can confirm external IP'),
            ('can_deploy_external_ip', 'Can implemet external IP'),
        ]


class BangusTask(Task):
    class Meta:
        proxy = True
