# -*- coding:utf-8 -*-

import os
import re
import json
from datetime import datetime

from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login, logout, models as auth_models
from django.conf import settings
from django.http.response import Http404
from django.views.decorators.csrf import csrf_exempt

from rest_framework import permissions, viewsets, status, views
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response


from .models import Profile
from .permissions import IsAccountOwner
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
