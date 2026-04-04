from rest_framework import viewsets, permissions
from .models import Project
from .serializers import ProjectSerializer
from django.views.decorators.cache import cache_page

from django.utils.decorators import method_decorator

@method_decorator(cache_page(60 * 5), name='list')
@method_decorator(cache_page(60 * 5), name='retrieve')
class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to create, view, update, and delete their own projects.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
