import yaml
from pathlib import Path
from opentelemetry import trace

tracer = trace.get_tracer("alert-engine")

def load_service_owners(file_path: str) -> dict[str, str]:
    with tracer.start_as_current_span("service_owners.load", attributes={"config.path": file_path}):
        path = Path(file_path)
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    return data.get("service_owners", {})
                return {}
        except Exception:
            return {}
