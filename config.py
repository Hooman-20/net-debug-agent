"""All settings in one place. Override any of them with an environment variable."""
import os

# Model
MODEL_BASE_URL = os.environ.get("MODEL_BASE_URL", "https://api.meta.ai/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "muse-spark-1.3")

# Where commands and generated tools run
NAMESPACE = os.environ.get("AGENT_NAMESPACE", "ns1")

# Discovery limits
MAX_DISCOVERY_STEPS = int(os.environ.get("MAX_DISCOVERY_STEPS", "10"))  # commands the model may run
MAX_BAD_REPLIES = 3       # unreadable replies before discovery gives up
CMD_TIMEOUT = 15          # seconds per discovery command
MAX_OUTPUT_CHARS = 4000   # command output sent back to the model is cut to this

SUMMARY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_summary.txt")
