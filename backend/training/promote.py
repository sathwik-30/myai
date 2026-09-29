"""Promote a validated decoder checkpoint into the runtime production slot."""
from pathlib import Path
import shutil

from backend.training.evaluate import DEFAULT_CHECKPOINT, PRODUCTION_CHECKPOINT, promotion_status

def promote(source: str | Path = DEFAULT_CHECKPOINT, destination: str | Path = PRODUCTION_CHECKPOINT):
    status = promotion_status(source)
    if not status["eligible"]:
        raise RuntimeError(
            "Checkpoint is not eligible for promotion. "
            f"validation_loss={status.get('validation_loss')!r}"
        )
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "promoted": True,
        "source": str(source),
        "destination": str(destination),
        "validation_loss": status["validation_loss"],
    }

if __name__ == "__main__":
    print(promote())
