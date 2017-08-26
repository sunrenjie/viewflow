# -*- coding:utf-8 -*-

import json

from django.core.exceptions import ViewDoesNotExist
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout, models as auth_models
from django.http.response import Http404
from django.views.decorators.csrf import csrf_exempt

from rest_framework import permissions, viewsets, status, views
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AccountSerializer


class LoginRestView(views.APIView):
    @csrf_exempt
    def post(self, request, format=None):
        # To convert request.body to json; works under Python 2 and 3; see also:
        # http://stackoverflow.com/questions/29514077/get-request-body-as-string-in-django
        body_unicode = request.body.decode('utf-8')
        data = json.loads(body_unicode)
        username = data.get('username', None)
        email = data.get('email', None)
        phone = data.get('phone', None)
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

        # Try to translate phone number to username
        if username is None and phone:
            try:
                profile = get_object_or_404(Profile.objects, phone=phone)
                username = profile.user.username
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
