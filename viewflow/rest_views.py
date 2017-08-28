# -*- coding:utf-8 -*-

import six
import json
from datetime import datetime

from django.core.exceptions import ViewDoesNotExist, PermissionDenied, ImproperlyConfigured
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout, models as auth_models
from django.http.response import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import ugettext_lazy as _

from rest_framework import permissions, status, views, exceptions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.compat import set_rollback

from .activation import STATUS
from .decorators import flow_view, flow_start_view
from .serializers import AccountSerializer, TaskSerializer, ProcessSerializer


class LoginRestView(views.APIView):
    @csrf_exempt
    def post(self, request, format=None):
        # To convert request.body to json; works under Python 2 and 3; see also:
        # http://stackoverflow.com/questions/29514077/get-request-body-as-string-in-django
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        username = data.get('username', None)
        email = data.get('email', None)
        password = data.get('password', None)

        # TODO how this shall be changed when the authentication policy change.
        # Try to translate email to username
        if username is None and email:
            try:
                user = get_object_or_404(auth_models.User, email=email)
                username = user.username
            except Http404 as e:
                # to return HTTP_401_UNAUTHORIZED consistently
                pass

        account = None
        if username:
            account = authenticate(password=password, username=username)

        if account is not None:
            if account.is_active:
                login(request, account)
                serialized = AccountSerializer(account)
                return Response(serialized.data)
            else:
                return Response({
                    'status': 'Unauthorized',
                    'message': 'This account has been disabled.'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({
                'status': 'Unauthorized',
                'message': 'Username/password combination invalid.'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutRestView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @csrf_exempt
    def post(self, request, format=None):
        logout(request)
        return Response({}, status=status.HTTP_204_NO_CONTENT)


class APIViewWithoutCSRFEnforcement(APIView):
    # Because rest_framework.authentication.SessionAuthentication.authenticate() enforces CSRF check, which is
    # against REST API spirit, here we do its authentication job in advance so that CSRF check is effectively worked
    # around.
    def initial(self, request, *args, **kwargs):
        user = request._request.user
        request.user = request._user = user
        return super(APIViewWithoutCSRFEnforcement, self).initial(request, *args, **kwargs)


class GenericAPIViewWithoutCSRFEnforcement(GenericAPIView, APIViewWithoutCSRFEnforcement):
    pass


class StartViewRest(GenericAPIViewWithoutCSRFEnforcement):
    process_serializer_class = ProcessSerializer

    # Derived class shall define the two.
    serializer_class = None
    object_field_name = None

    def __init__(self, **kwargs):
        super(StartViewRest, self).__init__(**kwargs)
        if not self.object_field_name:
            raise ImproperlyConfigured('The class "%s" shall define object_field_name.' % self.__class__.__name__)

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    def perform_create(self, serializer):
        # Injecting owner info into validated data.
        return serializer.save(owner=self.request.user)

    @method_decorator(flow_start_view)
    @csrf_exempt
    def post(self, request, *args, **kwargs):
        # Cannot be implemented within get_permissions(), because at which time activation is not yet assigned to
        # request. Having to putting the validation here is a sacrifice of insisting on using flow_start_view.
        # Alternatively, we may put things from flow_start_view partly self.initial() and partly into this method
        # (in particular, the call to activation.lock.__exit__() is very important, without which the next task won't
        # be created at all). Then we will be able access request.activation in get_permissions().
        if not request.activation.has_perm(request.user):
            raise PermissionDenied

        # Behind activation (type: viewflow.flow.activation.ManagedStartViewActivation), there is a
        # viewflow.forms.ActivationDataForm, which is responsible for injecting a started datetime value (with
        # prefix "_viewflow_activation" into the form for the start page. Upon POST, that value is sent back and taken
        # as a protection against misusages. Here we simply prepare that form in data; for the mechanisms, see also
        # django.forms.fields.DateTimeField.to_python().
        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        # Contents of CreateModelMixin.create() copied here. We do the copy because we want to make use of the
        # serializer (for returning validated data) and created order object (for assigning to the process).
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = self.perform_create(serializer)

        request.activation.done()
        setattr(request.process, self.object_field_name, obj)
        request.process.save()
        process_data = self.process_serializer_class(request.process).data
        return Response({'process': process_data, 'object': serializer.validated_data}, status=status.HTTP_201_CREATED)


class UpdateFieldsRestViewMixin(GenericAPIViewWithoutCSRFEnforcement):
    # Derived class shall:
    # 1. implement a dispatch annotated with flow_view or flow_start_view.
    # 2. implement a post that calls super post defined in this class and create a response.
    # 3. define a serializer_class for the business logic model, unless fields list is empty.

    serializer_class = None
    task_serializer_class = TaskSerializer
    fields = None  # required for it to accept fields arguments, yet be able to get through as_view() safely.

    def __init__(self, **kwargs):
        super(UpdateFieldsRestViewMixin, self).__init__(**kwargs)
        if self.fields is None:
            self.fields = []
        self.activation = None

    def get_permissions(self):
        # incomplete implementation here; see also #post().
        perms = [permissions.IsAuthenticated(), ]
        return perms

    def get_object(self, queyset=None):
        # Get the business logic model object. If the derived class defines its own logical model, it shall override
        # this method.
        return self.activation.process

    def get(self, request, *args, **kwargs):
        """Get the task details despite the class name."""
        task = self.activation.task
        task_data = self.task_serializer_class(task, request=request).data
        data = {'task': task_data}

        if self.serializer_class:
            obj = self.get_object()
            obj_data = self.serializer_class(obj).data
            data['object'] = obj_data
        return Response(data)

    def post(self, request, *args, **kwargs):
        if not self.activation.has_perm(request.user):
            # TODO More precise diagnostics info given to the user.
            # If the task is not yet assigned (status is NEW), we shall explicitly tell the user to assign it first.
            # If the task is creating a new process, but the user simply has no permission to do so, we shall also be
            # explicit about this.
            raise PermissionDenied("The user has not permission to perform the task.")

        # Errors going into the status machine can be hard to understand. Try to intercept.
        # Creating-new Tasks have NEW status.
        s = request.activation.status
        if s not in (STATUS.ASSIGNED, STATUS.NEW):
            msg_dict = {
                STATUS.DONE: 'The task is already finished.'
            }
            msg = msg_dict.get(s, "The task is in '%s' status, therefore cannot be performed." % s)
            raise PermissionDenied(msg)

        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        obj = self.get_object()

        # Give more precise diagnostics info.
        expected = set(self.fields)
        requested = set(request.data.keys())
        missing = expected - requested
        unexpected = requested - expected
        if missing:
            raise ValidationError('These attribute(s) are required: %s.' % str(missing))
        if unexpected:
            raise ValidationError('These attribute(s) are unexpected: %s.' % str(unexpected))

        if self.fields:  # Certain tasks may have no fields. We shall tolerate empty field list.
            serializer = self.get_serializer(obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()

        self.activation.done()

        # We are not returning a response here!
        # Derived-class shall override this method by getting this object and construct its own response message.
        return obj


class FinishAssignedTaskWithFieldsRestView(UpdateFieldsRestViewMixin):
    @method_decorator(flow_view)
    def dispatch(self, request, **kwargs):
        """Check user permissions, and prepare flow to execution."""
        self.activation = request.activation
        return super(UpdateFieldsRestViewMixin, self).dispatch(request, **kwargs)

    def post(self, request, *args, **kwargs):
        super(FinishAssignedTaskWithFieldsRestView, self).post(request, *args, **kwargs)
        return Response({'message': 'The task has been completed successfully.'})


class CreateProcessRestView(UpdateFieldsRestViewMixin):
    @method_decorator(flow_start_view)
    def dispatch(self, request, **kwargs):
        """Check user permissions, and prepare flow to execution."""
        self.activation = request.activation
        return super(UpdateFieldsRestViewMixin, self).dispatch(request, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = super(CreateProcessRestView, self).post(request, *args, **kwargs)
        return Response({'message': 'A new process (id=%s) is started.' % str(obj.id)})


class AssignTaskRestView(APIViewWithoutCSRFEnforcement):
    def get_permissions(self):
        perms = [permissions.IsAuthenticated()]
        return perms

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        namespace = self.request.resolver_match.namespace
        task_detail_url = self.activation.task.flow_task.get_task_url(
            self.activation.task, url_type='detail', user=self.request.user, namespace=namespace)

        if not self.activation.assign.can_proceed():
            return Response({'message': "The task is in '%s' status and cannot be assigned." %
                                        self.activation.task.status}, status=status.HTTP_409_CONFLICT)

        if not self.activation.flow_task.can_assign(request.user, self.activation.task):
            return Response({'message': 'The task cannot be assigned to you.'}, status=status.HTTP_403_FORBIDDEN)

        self.activation.assign(self.request.user)
        return Response({'messsage': 'Task has been assigned to you successfully.',
                         'link': {
                             'detail': task_detail_url
                         }})

    @method_decorator(flow_view)
    def dispatch(self, request, *args, **kwargs):
        self.activation = request.activation
        # The calls to can_proceed() and can_assign() have to be performed in post(), since at that point, we are
        # called by rest_framework.views.dispatch(), where proper work is done such that we could return a
        # rest_framework.response.Response object. Making the calls here will result in error.

        return super(AssignTaskRestView, self).dispatch(request, *args, **kwargs)


class UnassignTaskRestView(APIViewWithoutCSRFEnforcement):
    pass  # TODO implement it.


def get_view_with_rest_awareness(view, rest, **view_initkwargs):
    if rest:
        rest_view = getattr(view, 'REST_VERSION', None)
        if not rest_view:
            raise ViewDoesNotExist(
                'The rest version of the view "%s" is not available at its REST_VERSION attribute.' % str(view))
        view = rest_view
    if isinstance(view, type) and hasattr(view, 'as_view'):
        view = view.as_view(**view_initkwargs)
    return view


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'message': exc.detail}

        set_rollback()
        return Response(data, status=exc.status_code, headers=headers)

    elif isinstance(exc, Http404):
        msg = _('Not found.')
        data = {'message': six.text_type(msg)}

        set_rollback()
        return Response(data, status=status.HTTP_404_NOT_FOUND)

    elif isinstance(exc, PermissionDenied):
        data = {'message': six.text_type(_('Permission denied: %s') % exc.message)}

        set_rollback()
        return Response(data, status=status.HTTP_403_FORBIDDEN)

    return None
