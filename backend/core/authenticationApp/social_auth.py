from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.github.views import GitHubOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.shortcuts import redirect
from rest_framework.response import Response
from django.conf import settings
from urllib.parse import urlencode


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:8000/api/auth/google/callback/"
    client_class = OAuth2Client

    def get(self, request):
        params = {
            "client_id": settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id'],
            "redirect_uri": "http://localhost:8000/api/auth/google/callback/",
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",  # 🔥 Forces account selection popup
        }
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
        return redirect(google_auth_url)
 

class GoogleCallbackView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:8000/api/auth/google/callback/"
    client_class = OAuth2Client

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        error = request.GET.get("error")

        if error:
            return redirect(f"http://localhost:5173/login?error={error}")

        if not code:
            return redirect("http://localhost:5173/login?error=no_code")

        # ✅ Monkey-patch request.data — DRF reads THIS, not POST
        request._full_data = {"code": code}

        response = self.post(request, *args, **kwargs)

        if response.status_code == 200:
            token = response.data.get("access", response.data.get("key", ""))
            return redirect(f"http://localhost:5173/auth/callback?token={token}")

        return redirect(f"http://localhost:5173/login?error=auth_failed")


class GithubLoginView(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = "http://localhost:8000/api/auth/github/callback/"
    client_class = OAuth2Client

    def get(self, request):
        params = {
            "client_id": settings.SOCIALACCOUNT_PROVIDERS['github']['APP']['client_id'],
            "redirect_uri": "http://localhost:8000/api/auth/github/callback/",
            "scope": "read:user user:email",
            "prompt": "consent",  # 🔥 Forces GitHub authorization prompt
        }
        github_auth_url = "https://github.com/login/oauth/authorize?" + urlencode(params)
        return redirect(github_auth_url)


class GithubCallbackView(SocialLoginView):
    adapter_class = GitHubOAuth2Adapter
    callback_url = "http://localhost:8000/api/auth/github/callback/"
    client_class = OAuth2Client

    def get(self, request, *args, **kwargs):
        code = request.GET.get("code")
        error = request.GET.get("error")

        if error:
            return redirect(f"http://localhost:5173/login?error={error}")

        if not code:
            return redirect("http://localhost:5173/login?error=no_code")

        # ✅ Monkey-patch request.data — DRF reads THIS, not POST
        request._full_data = {"code": code}

        response = self.post(request, *args, **kwargs)

        if response.status_code == 200:
            token = response.data.get("access", response.data.get("key", ""))
            return redirect(f"http://localhost:5173/auth/callback?token={token}")

        return redirect(f"http://localhost:5173/login?error=auth_failed")