from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    serverIp = serializers.CharField(source="server_ip", max_length=100)
    rootDirectory = serializers.CharField(source="rootDir", max_length=100)

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "sshKey",
            "serverIp",
            "rootDirectory",
            "owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "owner", "created_at", "updated_at")

