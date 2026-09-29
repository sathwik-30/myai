from pathlib import Path
import math
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = PROJECT_ROOT / "models/checkpoints/medha-small.pt"
PRODUCTION_CHECKPOINT = PROJECT_ROOT / "models/production/medha-small.pt"

def checkpoint_exists(path: str | Path = DEFAULT_CHECKPOINT) -> bool:
    return Path(path).is_file()

def summarize_checkpoint(path: str | Path = DEFAULT_CHECKPOINT) -> dict:
    file = Path(path)
    result = {"path": str(file), "exists": file.is_file(), "size_bytes": file.stat().st_size if file.is_file() else 0}
    if not file.is_file():
        return result
    try:
        payload = torch.load(file, map_location="cpu", weights_only=False)
        result["config"] = payload.get("config", {})
        result["training"] = payload.get("training", {})
        loss = result["training"].get("validation_loss")
        result["finite_validation_loss"] = loss is not None and math.isfinite(float(loss))
    except Exception as exc:
        result["load_error"] = str(exc)
        result["finite_validation_loss"] = False
    return result

def production_checkpoint_exists() -> bool:
    return PRODUCTION_CHECKPOINT.is_file()

def promotion_status(path: str | Path = DEFAULT_CHECKPOINT) -> dict:
    summary = summarize_checkpoint(path)
    training = summary.get("training", {})
    loss = training.get("validation_loss")
    # Promotion is deliberately explicit. A low loss alone is not proof of
    # conversational competence, so training never silently becomes production.
    eligible = bool(summary.get("finite_validation_loss")) and float(loss) < 8.0
    return {
        "eligible": eligible,
        "validation_loss": loss,
        "requires_explicit_promotion": True,
        "production_checkpoint": str(PRODUCTION_CHECKPOINT),
    }
