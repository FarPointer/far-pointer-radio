"""Rule thresholds loaded from data instead of being hard-coded in source."""
import yaml
from paths import HERE

RULES_PATH = HERE / "rules.yaml"

RULES = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
