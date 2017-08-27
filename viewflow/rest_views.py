# -*- coding:utf-8 -*-

import json
from datetime import datetime

import django
from django.core.exceptions import ViewDoesNotExist, PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout, models as auth_models
from django.http.response import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework import permissions, viewsets, status, views
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from viewflow import STATUS
from viewflow.decorators import flow_view, flow_start_view
from .serializers import AccountSerializer, TaskSerializer


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
    serializer_class = None

    def __init__(self, **kwargs):
        super(StartViewRest, self).__init__(**kwargs)

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
        order = self.perform_create(serializer)

        request.process.order = order
        request.activation.done()
        return Response(serializer.data)


class UpdateFieldsRestViewMixin(GenericAPIViewWithoutCSRFEnforcement):
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

    @method_decorator(flow_view)
    def dispatch(self, request, **kwargs):
        """Check user permissions, and prepare flow to execution."""
        self.activation = request.activation
        return super(UpdateFieldsRestViewMixin, self).dispatch(request, **kwargs)

    @property
    def model(self):
        return self.activation.flow_class.process_class

    def get_object(self, queyset=None):
        # Get the business logic model object. If the derived class defines its own logical model, it shall override
        # this method.
        return self.activation.process

    def get(self, request, *args, **kwargs):
        if not self.serializer_class:
            raise PermissionDenied('No serializer class is defined for this task.')
        obj = self.get_object()
        obj_data = self.get_serializer(obj).data
        task = self.activation.task
        task_data = self.task_serializer_class(task).data
        return Response({'object': obj_data, 'task': task_data})

    def post(self, request, *args, **kwargs):
        if not self.activation.has_perm(request.user):
            raise PermissionDenied("The user has not permission to perform the task.")
        if request.activation.status == STATUS.DONE:
            raise PermissionDenied("The task is already finished.")

        request.activation.prepare({'_viewflow_activation-started': datetime.now()}, user=request.user)

        obj = self.get_object()
        for attr, value in request.data.items():
            if attr not in self.fields:
                raise ValidationError("'%s' is not one of the attributes this task is designed to change. "
                                      "Allowed attributes are %s." % (attr, str(self.fields)))
            setattr(obj, attr, value)
        try:
            obj.save()
        except django.core.exceptions.ValidationError as e:
            # Translate the django version of exception to a Rest Framework version, so that the Rest Framework may
            # do the rest of work.
            raise ValidationError({'messages': e.messages})

        self.activation.done()

        # Derived-class shall override this method by getting this object and construct its own response message.
        return obj


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
