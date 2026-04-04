import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer

# Load .env from the backend directory (one level above core/)
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8000")

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

    @action(detail=True, methods=["post"], url_path="run-agent")
    def run_agent(self, request, pk=None):
        """
        POST /api/user-projects/{id}/run-agent/

        Triggers the AI engine agent for this specific project.
        Runs the LangGraph agent inline (same process) so no separate
        AI engine service is needed.
        """
        import uuid
        import sys
        from pathlib import Path as SysPath

        project = self.get_object()  # enforces ownership via get_queryset

        source = request.data.get("source", "frontend_trigger")
        service_hint = request.data.get("service_hint", None)
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"

        # Add the ai_engine directory to sys.path so we can import the agent
        ai_engine_path = str(SysPath(__file__).resolve().parent.parent.parent / "ai_engine")
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        try:
            from pathlib import Path as P
            from dotenv import load_dotenv
            _env = (P(ai_engine_path) / ".env").resolve()
            load_dotenv(_env)
            gemini_key = os.getenv("GEMINI_API_KEY", "NOT-FOUND")
            print(f"[DEBUG] ai_engine .env = {_env}")
            print(f"[DEBUG] GEMINI_API_KEY = {gemini_key[:8]}...{gemini_key[-4:] if len(gemini_key) > 12 else gemini_key}")

            from graph import agent  # import the compiled LangGraph agent

            initial_state = {
                "incident_id": incident_id,
                "project_id": project.id,
                "source": source,
                "service_hint": service_hint,
                # ── Project credentials — passed to the agent so it can connect ──
                "ssh_key": project.sshKey,
                "server_ip": project.server_ip,
                "root_dir": project.rootDir,
                "deploy_commands": project.userDeployCommands,
            }

            result = agent.invoke(initial_state)

            return Response({
                "incident_id": incident_id,
                "project_id": project.id,
                "status": "completed",
                "resolved": result.get("incident_resolved"),
                "summary": result.get("final_summary"),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e), "incident_id": incident_id},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
