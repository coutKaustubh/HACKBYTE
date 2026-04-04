import os
import sys
import uuid
import json
import asyncio
import threading
import queue
import httpx
from pathlib import Path
from dotenv import load_dotenv
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import StreamingHttpResponse
from .models import Project
from .serializers import ProjectSerializer
from rest_framework.renderers import BaseRenderer


class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'sse'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
AI_ENGINE_URL = os.getenv("AI_ENGINE_URL", "http://localhost:8000")

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
    @action(detail=True, methods=["get"], url_path="run-agent-stream", renderer_classes=[SSERenderer])
    def run_agent_stream(self, request, pk=None):
        """
        GET /api/user-projects/{id}/run-agent-stream/

        Streams LangGraph pipeline events as Server-Sent Events (SSE).
        The frontend connects with EventSource and receives JSON lines.
        """
        project = self.get_object() # This will fail if not authenticated via headers
        
        # ... logic if we want to allow query param auth ...
        # (Actually, DRF's JWTAuthentication won't see query params by default)
        
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        source = request.GET.get("source", "frontend_trigger")
        service_hint = request.GET.get("service_hint", None)

        ai_engine_path = str(Path(__file__).resolve().parent.parent.parent / "ai_engine")
        if ai_engine_path not in sys.path:
            sys.path.insert(0, ai_engine_path)

        # Load ai_engine .env so GEMINI_API_KEY is available
        from pathlib import Path as P
        _env = (P(ai_engine_path) / ".env").resolve()
        load_dotenv(_env)

        initial_state = {
            "incident_id": incident_id,
            "project_id": project.id,
            "source": source,
            "service_hint": service_hint,
            "ssh_key": project.sshKey,
            "server_ip": project.server_ip,
            "root_dir": project.rootDir,
            "deploy_commands": project.userDeployCommands,
        }

        # ── Run async generator in a background thread, bridge via queue ──────
        event_queue = queue.Queue()

        def run_async_in_thread():
            from graph import stream_agent_events
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async def collect():
                    async for evt in stream_agent_events(initial_state):
                        event_queue.put(evt)
                loop.run_until_complete(collect())
            finally:
                event_queue.put(None)  # sentinel: stream done
                loop.close()

        thread = threading.Thread(target=run_async_in_thread, daemon=True)
        thread.start()

        def sse_generator():
            """Yield SSE-formatted lines consumed by EventSource."""
            yield f"data: {json.dumps({'event':'stream_start','incident_id': incident_id})}\n\n"
            while True:
                item = event_queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item)}\n\n"
            yield f"data: {json.dumps({'event':'stream_end'})}\n\n"

        response = StreamingHttpResponse(
            sse_generator(),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
