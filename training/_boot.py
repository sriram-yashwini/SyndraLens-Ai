import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)

import yaml

def load_config(path="configs/config.yaml"):
    with open(path, encoding="utf-8-sig") as f:
        return yaml.safe_load(f)
