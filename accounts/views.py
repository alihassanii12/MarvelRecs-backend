from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.conf import settings

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user': UserSerializer(user).data,
                'tokens': get_tokens_for_user(user),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email aur password dono zaroori hain.'}, status=400)

        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials.'}, status=401)

        if user_obj.is_google_user and not user_obj.has_usable_password():
            return Response(
                {'error': 'Yeh account Google se bana hai. Google se login karein.'},
                status=400
            )

        user = authenticate(username=email, password=password)
        if user is None:
            return Response({'error': 'Invalid credentials.'}, status=401)

        return Response({
            'user': UserSerializer(user).data,
            'tokens': get_tokens_for_user(user),
        })


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('id_token')
        if not token:
            return Response({'error': 'id_token missing.'}, status=400)

        try:
            idinfo = id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response({'error': 'Invalid Google token.'}, status=401)

        email = idinfo.get('email')
        google_id = idinfo.get('sub')

        if not email:
            return Response({'error': 'Google token se email nahi mila.'}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'is_google_user': True,
                'google_id': google_id,
                'profile_picture': idinfo.get('picture', ''),
            }
        )

        # agar user pehle manual se bana tha, ab google se bhi link ho jaye
        if not created and not user.is_google_user:
            user.is_google_user = True
            user.google_id = google_id
            if not user.profile_picture:
                user.profile_picture = idinfo.get('picture', '')
            user.save()

        return Response({
            'user': UserSerializer(user).data,
            'created': created,
            'tokens': get_tokens_for_user(user),
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)