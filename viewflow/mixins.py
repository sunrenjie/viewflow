from copy import copy
from textwrap import dedent
from django.conf.urls import url
from django.core.urlresolvers import reverse

from . import Edge


class NextNodeMixin(object):
    """
    Single next node mixin
    """
    def __init__(self, *args, **kwargs):
        self._next = None
        super(NextNodeMixin, self).__init__(*args, **kwargs)

    def Next(self, node):
        result = copy(self)
        result._next = node
        return result

    def _resolve(self, resolver):
        if self._next:
            self._next = resolver.get_implementation(self._next)

    def _outgoing(self):
        if self._next:
            yield Edge(src=self, dst=self._next, edge_class='next')


class DetailViewMixin(object):
    detail_view_class = None

    def __init__(self, *args, **kwargs):
        self._detail_view = kwargs.pop('detail_view', None)
        super(DetailViewMixin, self).__init__(*args, **kwargs)

    @property
    def detail_view(self):
        return self._detail_view if self._detail_view else self.detail_view_class.as_view()

    def urls(self, rest=False):
        urls = super(DetailViewMixin, self).urls(rest=rest)
        urls.append(
            url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/detail/$'.format(self.name),
                self.detail_view, {'flow_task': self}, name="{}__detail".format(self.name))
        )
        return urls

    def get_task_url(self, task, url_type='guess', namespace='', **kwargs):
        if url_type in ['detail', 'guess']:
            url_name = '{}:{}__detail'.format(namespace, self.name)
            return reverse(url_name, args=[task.process_id, task.pk])
        return super(DetailViewMixin, self).get_task_url(task, url_type, namespace=namespace, **kwargs)

    def can_view(self, user, task):
        return user.has_perm(self.flow_class.instance.view_permission_name)


class UndoViewMixin(object):
    undo_view_class = None

    def __init__(self, *args, **kwargs):
        self._undo_view = kwargs.pop('undo_view', None)
        super(UndoViewMixin, self).__init__(*args, **kwargs)

    @property
    def undo_view(self):
        return self._undo_view if self._undo_view else self.undo_view_class.as_view()

    def urls(self, rest=False):
        urls = super(UndoViewMixin, self).urls(rest=rest)
        urls.append(
            url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/undo/$'.format(self.name),
                self.undo_view, {'flow_task': self}, name="{}__undo".format(self.name))
        )
        return urls

    def get_task_url(self, task, url_type='guess', namespace='', **kwargs):
        if url_type in ['undo']:
            url_name = '{}:{}__undo'.format(namespace, self.name)
            return reverse(url_name, args=[task.process_id, task.pk])
        return super(UndoViewMixin, self).get_task_url(task, url_type, namespace=namespace, **kwargs)


class CancelViewMixin(object):
    cancel_view_class = None

    def __init__(self, *args, **kwargs):
        self._cancel_view = kwargs.pop('cancel_view', None)
        super(CancelViewMixin, self).__init__(*args, **kwargs)

    def cancel_view(self, rest=False):
        return self._cancel_view if self._cancel_view else self.cancel_view_class.as_view()

    def urls(self, rest=False):
        urls = super(CancelViewMixin, self).urls(rest=rest)
        urls.append(
            url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/cancel/$'.format(self.name),
                self.cancel_view(rest=rest), {'flow_task': self}, name="{}__cancel".format(self.name))
        )
        return urls

    def get_task_url(self, task, url_type='guess', namespace='', **kwargs):
        if url_type in ['cancel']:
            url_name = '{}:{}__cancel'.format(namespace, self.name)
            return reverse(url_name, args=[task.process_id, task.pk])
        return super(CancelViewMixin, self).get_task_url(task, url_type, namespace=namespace, **kwargs)


class PerformViewMixin(object):
    perform_view_class = None

    def __init__(self, *args, **kwargs):
        self._perform_view = kwargs.pop('perform_view', None)
        super(PerformViewMixin, self).__init__(*args, **kwargs)

    @property
    def perform_view(self):
        return self._perform_view if self._perform_view else self.perform_view_class.as_view()

    def urls(self, rest=False):
        urls = super(PerformViewMixin, self).urls(rest=rest)
        urls.append(url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/perform/$'.format(self.name),
                    self.perform_view, {'flow_task': self}, name="{}__perform".format(self.name)))
        return urls

    def get_task_url(self, task, url_type='guess', namespace='',  **kwargs):
        if url_type in ['perform']:
            url_name = '{}:{}__perform'.format(namespace, self.name)
            return reverse(url_name, args=[task.process_id, task.pk])
        return super(PerformViewMixin, self).get_task_url(task, url_type, namespace=namespace, **kwargs)


class ActivateNextMixin(object):
    activate_next_view_class = None

    def __init__(self, *args, **kwargs):
        self._activate_next_view = kwargs.pop('activate_next_view', None)
        super(ActivateNextMixin, self).__init__(*args, **kwargs)

    @property
    def activate_next_view(self):
        return self._activate_next_view if self._activate_next_view else self.activate_next_view_class.as_view()

    def urls(self, rest=False):
        urls = super(ActivateNextMixin, self).urls(rest=rest)
        urls.append(
            url(r'^(?P<process_pk>\d+)/{}/(?P<task_pk>\d+)/activate_next/$'.format(self.name),
                self.activate_next_view, {'flow_task': self}, name="{}__activate_next".format(self.name))
        )
        return urls

    def get_task_url(self, task, url_type='guess', namespace='', **kwargs):
        if url_type in ['activate_next']:
            url_name = '{}:{}__activate_next'.format(namespace, self.name)
            return reverse(url_name, args=[task.process_id, task.pk])
        return super(ActivateNextMixin, self).get_task_url(task, url_type, namespace=namespace, **kwargs)


class PermissionMixin(object):
    """
    Node mixing with permission restricted access
    """
    def __init__(self, *args, **kwargs):
        self._owner = None
        self._owner_permission = None
        self._owner_permission_auto_create = False
        self._owner_permission_help_text = None

        super(PermissionMixin, self).__init__(*args, **kwargs)

    def Permission(self, permission=None, auto_create=False, obj=None, help_text=None):
        """
        Make task available for users with specific permission,
        aceps permissions name of callable :: Activation -> permission_name::

            .Permission('my_app.can_approve')
            .Permission(lambda process: 'my_app.department_manager_{}'.format(process.depratment.pk))

        Task specific permission could be auto created during migration::

            # Creates `processcls_app.can_do_task_processcls` permission
            do_task = View().Permission(auto_create=True)

            # You can specify permission codename and description right here
            # The following creates `processcls_app.can_execure_task` permission
            do_task = View().Permission('can_execute_task', help_text='Custom text', auto_create=True)
        """
        if permission is None and not auto_create:
            raise ValueError('Please specify existion permission name or mark as auto_create=True')

        result = copy(self)
        result._owner_permission = permission
        result._owner_permission_obj = obj
        result._owner_permission_auto_create = auto_create
        result._owner_permission_help_text = help_text
        return result

    def ready(self):
        if self._owner_permission_auto_create:
            if self._owner_permission and '.' in self._owner_permission:
                raise ValueError('Non qualified permission name expected')

            if not self._owner_permission:
                self._owner_permission = 'can_{}_{}'.format(
                    self.name, self.flow_class.process_class._meta.model_name)
                self._owner_permission_help_text = 'Can {}'.format(
                    self.name.replace('_', ' '))
            elif not self._owner_permission_help_text:
                self._owner_permission_help_text = self._owner_permission.replace('_', ' ').capitalize()

            for codename, _ in self.flow_class.process_class._meta.permissions:
                if codename == self._owner_permission:
                    break
            else:
                self.flow_class.process_class._meta.permissions.append(
                    (self._owner_permission, self._owner_permission_help_text))

            self._owner_permission = '{}.{}'.format(self.flow_class.process_class._meta.app_label, self._owner_permission)

        super(PermissionMixin, self).ready()


class TaskDescriptionMixin(object):
    task_title = None
    task_description = None
    task_result_summary = None

    def __init__(self, view_or_class=None, task_title=None, task_description=None, task_result_summary=None, **kwargs):
        if task_title:
            self.task_title = task_title
        if task_description:
            self.task_description = task_description
        if task_result_summary:
            self.task_result_summary = task_result_summary

        super(TaskDescriptionMixin, self).__init__(**kwargs)


class TaskDescriptionViewMixin(TaskDescriptionMixin):
    """
    Extract task desctiption from view docstring
    """

    def __init__(self, view_or_class=None, **kwargs):
        super(TaskDescriptionViewMixin, self).__init__(**kwargs)

        if view_or_class:
            if view_or_class.__doc__ and (self.task_title is None or self.task_description is None):
                docstring = view_or_class.__doc__.split('\n\n', 1)
                if self.task_title is None and len(docstring) > 0:
                    self.task_title = docstring[0].strip()
                if self.task_description is None and len(docstring) > 1:
                    self.task_description = dedent(docstring[1]).strip()
            if hasattr(view_or_class, 'task_result_summary') and self.task_result_summary is None:
                self.task_result_summary = view_or_class.task_result_summary


class ViewArgsMixin(object):
    """
    Capture rest of kwargs as view kwargs.
    Put this mixing always the last in inheritance order
    """
    def __init__(self, **kwargs):
        self._view_args = kwargs
