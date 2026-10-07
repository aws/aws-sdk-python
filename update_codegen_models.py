#!/usr/bin/env python3
"""Update the selected codegen models from a local aws-models checkout."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


DEFAULT_AWS_MODELS_REPO = Path("~/dev/GitHub/aws-models").expanduser()
MODEL_DIRECTORY_OVERRIDES = {
    "api-gateway": "apigateway",
    "lex-runtime-v2": "runtime.lex.v2",
    "secrets-manager": "secretsmanager"
}


def run_git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def update_aws_models(repository: Path) -> None:
    if not (repository / ".git").exists():
        raise RuntimeError(f"{repository} is not a Git repository")

    tracked_changes = run_git(
        repository, "status", "--porcelain", "--untracked-files=no"
    )
    if tracked_changes:
        raise RuntimeError(
            f"{repository} has tracked changes; refusing to update it"
        )

    remotes = set(run_git(repository, "remote").splitlines())
    remote = "upstream" if "upstream" in remotes else "origin"
    if remote not in remotes:
        raise RuntimeError(
            f"{repository} has neither an upstream nor an origin remote"
        )

    run_git(repository, "switch", "master")
    run_git(repository, "pull", "--ff-only", remote, "master")


def copy_codegen_models(repository: Path, destination: Path) -> int:
    destination_models = sorted(destination.glob("*.json"))
    if not destination_models:
        raise RuntimeError(f"no model files found in {destination}")

    copies: list[tuple[Path, Path]] = []
    for destination_model in destination_models:
        service_name = destination_model.stem
        source_directory = MODEL_DIRECTORY_OVERRIDES.get(
            service_name, service_name
        )
        source_model = repository / source_directory / "smithy" / "model.json"
        if not source_model.is_file():
            raise RuntimeError(
                f"no Smithy model found for {service_name}: {source_model}"
            )
        copies.append((source_model, destination_model))

    for source_model, destination_model in copies:
        shutil.copyfile(source_model, destination_model)
        print(f"Copied {source_model} -> {destination_model}")

    return len(copies)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Update aws-models and copy Smithy models for the services already "
            "present in codegen/aws-models."
        )
    )
    parser.add_argument(
        "--aws-models-repo",
        type=Path,
        default=DEFAULT_AWS_MODELS_REPO,
        help=f"aws-models checkout (default: {DEFAULT_AWS_MODELS_REPO})",
    )
    parser.add_argument(
        "--skip-update",
        action="store_true",
        help="copy models without updating the aws-models checkout",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    aws_models_repo = args.aws_models_repo.expanduser().resolve()
    repository_root = Path(__file__).resolve().parent
    destination = repository_root / "codegen" / "aws-models"

    if not args.skip_update:
        update_aws_models(aws_models_repo)

    count = copy_codegen_models(aws_models_repo, destination)
    print(f"Updated {count} codegen models.")


if __name__ == "__main__":
    main()
