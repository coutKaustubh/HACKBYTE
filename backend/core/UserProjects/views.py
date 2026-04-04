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
        # Persist all validated serializer fields (name, description, sshKey, server_ip,
        # rootDir, userDeployCommands) and attach the authenticated user as owner.
        serializer.save(owner=self.request.user)
