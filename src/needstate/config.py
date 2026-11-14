"""Configuration paths are resolved relative to the project config, never the shell directory."""
from dataclasses import dataclass
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]

def read_yaml(path):
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

@dataclass
class Config:
    input_path: Path
    mapping: dict
    hierarchy: dict
    need_states: dict
    abbreviations: dict
    params: dict
    lens: dict
    synthetic: bool = False

def load_config(path="configs/pipeline.yaml"):
    path = Path(path).resolve()
    cfg = read_yaml(path)
    base = path.parent.parent
    def resolve(value):
        p = Path(value)
        return p if p.is_absolute() else base / p
    return Config(
        resolve(cfg["input"]["path"]), read_yaml(resolve(cfg["input"]["mapping"])),
        read_yaml(resolve(cfg["hierarchy"])), read_yaml(resolve(cfg["need_states"])),
        read_yaml(resolve(cfg["abbreviations"])).get("abbreviations", {}),
        cfg.get("params", {}), cfg.get("portfolio_lens", {}), cfg.get("synthetic", False),
    )
