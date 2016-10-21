# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import demo.orderit.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('viewflow', '0005_rename_flowcls'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.CharField(default=demo.orderit.models.generate_random_order_id_with_full_datetime_prefix, max_length=26, editable=False, primary_key=True, serialize=False)),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('vms_amended', models.BooleanField(default=False, verbose_name='VM order is amended?')),
                ('vms_request_for_review', models.BooleanField(default=False, verbose_name='VM order waiting for review?')),
                ('vms_verified', models.BooleanField(default=False, verbose_name='VM order verified')),
                ('vms_confirmed', models.BooleanField(default=False, verbose_name='VM order confirmed')),
                ('vms_deployed', models.BooleanField(default=False, verbose_name='VM order deployed')),
                ('vms_software_installed', models.BooleanField(default=False, verbose_name='VM software installed')),
                ('security_fixed', models.BooleanField(default=False, verbose_name='Security fixed')),
                ('security_confirmed', models.BooleanField(default=False, verbose_name='Security clear status confirmed')),
                ('external_ip', models.CharField(max_length=1024, verbose_name='External IP')),
                ('external_ip_confirmed', models.BooleanField(default=False, verbose_name='External IP confirmed')),
                ('external_ip_deployed', models.BooleanField(default=False, verbose_name='External IP deployed')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderItCompleteProjectProcess',
            fields=[
                ('process_ptr', models.OneToOneField(primary_key=True, parent_link=True, auto_created=True, serialize=False, to='viewflow.Process')),
                ('order', models.ForeignKey(null=True, to='orderit.Order', verbose_name='排序', blank=True)),
            ],
            options={
                'verbose_name_plural': 'Order complete project process list',
                'permissions': [('can_start_order', 'Can initiate an order process'), ('can_verify_order', 'Can verify that an order is technically possible'), ('can_confirm_order', 'Can confirm an order'), ('can_deploy_virtual_machines', 'Can deploy virtual machines'), ('can_confirm_security_status', 'Can confirm that the VMs are secure according to security scan'), ('can_confirm_external_ip', 'Can confirm external IP'), ('can_deploy_external_ip', 'Can implemet external IP')],
            },
            bases=('viewflow.process',),
        ),
        migrations.CreateModel(
            name='OrderVM',
            fields=[
                ('id', models.CharField(default=demo.orderit.models.generate_random_vm_id_with_full_datetime_prefix, max_length=23, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=16, verbose_name='VM Name')),
                ('sockets', models.IntegerField(verbose_name='VM CPU #sockets')),
                ('cores_per_socket', models.IntegerField(verbose_name='VM CPU #cores per #socket')),
                ('memory_GB', models.IntegerField(verbose_name='VM memory(GB)')),
                ('disks', models.CharField(max_length=32, verbose_name='VM disks')),
                ('nics', models.CharField(max_length=1024, verbose_name='VM NICs')),
                ('order', models.ForeignKey(to='orderit.Order', verbose_name='排序', related_name='VMs')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.CharField(default=demo.orderit.models.generate_uuid_hex, max_length=36, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32, verbose_name='Project')),
                ('owner', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, verbose_name='Owner')),
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
            field=models.ForeignKey(editable=False, to='orderit.Project', verbose_name='Project'),
        ),
        migrations.AddField(
            model_name='order',
            name='project',
            field=models.ForeignKey(to='orderit.Project', verbose_name='Project'),
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
