import subprocess
import sys
from pathlib import Path

# Cambiar al directorio del dashboard
dashboard_path = Path(__file__).parent / "dashboard"

# Ejecutar Streamlit
subprocess.run([
    sys.executable,
    "-m",
    "streamlit",
    "run",
    str(dashboard_path / "app.py"),
    "--server.port=8501",
    "--server.address=localhost"
])
