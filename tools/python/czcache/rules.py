"""Rule thresholds loaded from data instead of being hard-coded in source."""
import yaml
from paths import HERE

RULES_PATH = HERE / "rules.yaml"


def _load_rules(path):
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"rules file not found: {path}") from None
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in rules file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise TypeError(
            f"rules file must be a YAML mapping, got {type(data).__name__}: {path}"
        )
    return data


RULES = _load_rules(RULES_PATH)
