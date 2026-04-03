from rest_framework import viewsets, permissions
from .models import Project
from .serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to create, view, update, and delete their own projects.
    """
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users can only see their own projects
        return Project.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the owner to the current authenticated user
        serializer.save(owner=self.request.user)
