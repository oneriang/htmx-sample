# config.py
from pathlib import Path
import yaml

def load_config():
    config_path = Path(__file__).parent / "config/app.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)