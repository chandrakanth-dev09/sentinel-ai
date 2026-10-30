import argparse
import json
from pathlib import Path

from app.core.config import PROJECT_ROOT, settings
from app.ml.training import train_evaluate_and_save


def _default_output_path() -> Path:
    configured = Path(settings.MODEL_PATH)
    return configured if configured.is_absolute() else PROJECT_ROOT / configured


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the SentinelAI anomaly model.")
    parser.add_argument("--output", type=Path, default=_default_output_path())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--training-samples", type=int, default=3000)
    parser.add_argument("--evaluation-normal-samples", type=int, default=400)
    parser.add_argument("--anomalies-per-scenario", type=int, default=100)
    args = parser.parse_args()

    _, metrics = train_evaluate_and_save(
        output_path=args.output,
        seed=args.seed,
        training_samples=args.training_samples,
        evaluation_normal_samples=args.evaluation_normal_samples,
        anomalies_per_scenario=args.anomalies_per_scenario,
    )
    print(json.dumps({"artifact": str(args.output.resolve()), "evaluation": metrics}, indent=2))


if __name__ == "__main__":
    main()
