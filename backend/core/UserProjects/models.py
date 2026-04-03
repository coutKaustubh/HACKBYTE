from django.db import models
from django.conf import settings
# Create your models here.

 
class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    description = models.TextField(blank=True)

    server_ip = models.CharField(max_length=100)
    server_config = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive')

    created_at = models.DateTimeField(auto_now_add=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    last_deployment_date = models.DateTimeField(null=True, blank=True)

    special_features = models.JSONField(default=dict, blank=True)

    log_source_path = models.CharField(max_length=500)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self):
        return f"{self.name} ({self.owner.email})"