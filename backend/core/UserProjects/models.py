from django.db import models
from django.conf import settings

DEFAULT_USER_DEPLOY_COMMANDS = (
    "npm install && npm run build > logs/build.log 2>&1 && npm start"
)


class Project(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    description = models.TextField(blank=True)
    sshKey = models.CharField(max_length = 500)
    server_ip = models.CharField(max_length=100)
    rootDir = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    userDeployCommands = models.TextField(
        blank=True,
        default=DEFAULT_USER_DEPLOY_COMMANDS,
    )

    def save(self, *args, **kwargs):
        if not (self.userDeployCommands or "").strip():
            self.userDeployCommands = DEFAULT_USER_DEPLOY_COMMANDS
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return f"{self.name} ({self.owner.email})"