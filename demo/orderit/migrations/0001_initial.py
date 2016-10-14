# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demo.orderit.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('viewflow', '0005_rename_flowcls'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.CharField(editable=False, default=demo.orderit.models.generate_random_order_id_with_full_datetime_prefix, max_length=26, primary_key=True, serialize=False)),
                ('is_active', models.BooleanField(default=True)),
                ('vms_amended', models.BooleanField(default=False)),
                ('vms_request_for_review', models.BooleanField(default=False)),
                ('vms_verified', models.BooleanField(default=False)),
                ('vms_confirmed', models.BooleanField(default=False)),
                ('vms_deployed', models.BooleanField(default=False)),
                ('vms_software_installed', models.BooleanField(default=False)),
                ('security_fixed', models.BooleanField(default=False)),
                ('security_confirmed', models.BooleanField(default=False)),
                ('external_ip', models.CharField(max_length=1024)),
                ('external_ip_confirmed', models.BooleanField(default=False)),
                ('external_ip_deployed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItCompleteProjectProcess',
            fields=[
                ('process_ptr', models.OneToOneField(to='viewflow.Process', serialize=False, auto_created=True, primary_key=True, parent_link=True)),
                ('order', models.ForeignKey(to='orderit.Order', null=True, blank=True)),
            ],
            options={
                'permissions': [('can_start_order', 'Can initiate an order process'), ('can_verify_order', 'Can verify that an order is technically possible'), ('can_confirm_order', 'Can confirm an order'), ('can_deploy_virtual_machines', 'Can deploy virtual machines'), ('can_confirm_security_status', 'Can confirm that the VMs are secure according to security scan'), ('can_confirm_external_ip', 'Can confirm external IP'), ('can_deploy_external_ip', 'Can implemet external IP')],
                'verbose_name_plural': 'Order complete project process list',
            },
            bases=('viewflow.process',),
        ),
        migrations.CreateModel(
            name='OrderVM',
            fields=[
                ('id', models.CharField(editable=False, default=demo.orderit.models.generate_random_vm_id_with_full_datetime_prefix, max_length=23, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=16)),
                ('sockets', models.IntegerField()),
                ('cores_per_socket', models.IntegerField()),
                ('memory_GB', models.IntegerField()),
                ('disks', models.CharField(max_length=32)),
                ('nics', models.CharField(max_length=1024)),
                ('order', models.ForeignKey(to='orderit.Order', related_name='VMs')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.CharField(editable=False, default=demo.orderit.models.generate_uuid_hex, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32)),
                ('owner', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='BangusTask',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('viewflow.task',),
        ),
        migrations.AddField(
            model_name='ordervm',
            name='project',
            field=models.ForeignKey(editable=False, to='orderit.Project'),
        ),
        migrations.AddField(
            model_name='order',
            name='project',
            field=models.ForeignKey(to='orderit.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='project',
            unique_together=set([('owner', 'name')]),
        ),
        migrations.AlterUniqueTogether(
            name='ordervm',
            unique_together=set([('project', 'name')]),
        ),
    ]
