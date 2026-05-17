import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.agent.hf_client import HFClient, HFClientError


def main():
    c = HFClient()

    try:
        print(c.chat([{"role": "user", "content": "Hello"}]))
    except HFClientError as e:
        print("HF error:", e)


if __name__ == "__main__":
    main()
