#!/usr/bin/env python3
"""Generate one aws-sdk-python client from its service model via smithy-python codegen.

Usage: python codegen/gen_client.py <name>
  <name> accepts dynamodb, aws_sdk_dynamodb, aws-sdk-dynamodb, or bedrock-runtime forms.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

CODEGEN_DIR = Path(__file__).resolve().parent
REPO = CODEGEN_DIR.parent
MODELS = CODEGEN_DIR / "aws-models"
CLIENTS = REPO / "clients"
PROJECT = "aws-sdk-python-codegen"


def resolve_model(name: str) -> Path:
    """Map any client-name form to its aws-models/<model>.json file."""
    key = name.strip()
    for prefix in ("aws-sdk-", "aws_sdk_"):
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    # Models are hyphenated on disk; accept underscores too.
    candidates = {key, key.replace("_", "-"), key.replace("-", "_")}
    for cand in candidates:
        model = MODELS / f"{cand}.json"
        if model.exists():
            return model
    available = sorted(p.stem for p in MODELS.glob("*.json"))
    sys.exit(
        f"no model for '{name}' in {MODELS}\navailable: {', '.join(available)}"
    )


def service_id(model: Path) -> str:
    shapes = json.loads(model.read_text())["shapes"]
    services = [k for k, v in shapes.items() if v.get("type") == "service"]
    if len(services) != 1:
        sys.exit(f"expected exactly one service shape in {model.name}, found {services}")
    return services[0]


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: gen_client.py <client-name>")

    model = resolve_model(sys.argv[1])
    slug = model.stem                       # e.g. bedrock-runtime
    module = "aws_sdk_" + slug.replace("-", "_")   # aws_sdk_bedrock_runtime
    client_dir_name = "aws-sdk-" + slug     # aws-sdk-bedrock-runtime
    svc = service_id(model)

    version = "0.0.1"
    client_pyproject = CLIENTS / client_dir_name / "pyproject.toml"
    if client_pyproject.exists():
        for line in client_pyproject.read_text().splitlines():
            if line.startswith("version"):
                version = line.split("=", 1)[1].strip().strip('"')
                break

    build_config = {
        "version": "1.0",
        "imports": [str(model)],
        "projections": {
            slug: {
                "transforms": [
                    {"name": "includeServices", "args": {"services": [svc]}},
                    {"name": "removeUnusedShapes"},
                ],
                "plugins": {
                    "python-client-codegen": {
                        "service": svc,
                        "module": module,
                        "moduleVersion": version,
                    }
                },
            }
        },
    }
    build_file = CODEGEN_DIR / "smithy-build.json"
    build_file.write_text(json.dumps(build_config, indent=4) + "\n")
    print(f"generating {client_dir_name} ({svc}) -> module {module} v{version}")

    subprocess.run(
        [str(CODEGEN_DIR / "gradlew"), "-p", str(CODEGEN_DIR), "clean", "build", "-q"],
        check=True,
    )

    projection = (
        CODEGEN_DIR / "build" / "smithyprojections" / PROJECT / slug / "python-client-codegen"
    )
    if not projection.is_dir():
        sys.exit(f"codegen produced no output at {projection}")

    dest_src = CLIENTS / client_dir_name / "src" / module
    if dest_src.exists():
        shutil.rmtree(dest_src)
    dest_src.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(projection / "src" / module, dest_src)

    _format(dest_src, CLIENTS / client_dir_name / "pyproject.toml")
    print(f"wrote {dest_src}")


def _format(src_dir: Path, config: Path) -> None:
    """Format generated code with smithy-python's lockfile-pinned ruff.

    The generator only formats when ruff is on its own PATH, which gradle's env
    lacks; run the pinned formatter explicitly so output matches committed style.
    """
    import os

    smithy_python = Path(os.environ.get("SMITHY_PYTHON", REPO.parent / "smithy-python"))
    if not (smithy_python / "pyproject.toml").exists():
        print(f"skipping ruff: no smithy-python checkout at {smithy_python}")
        return
    cfg = ["--config", str(config)] if config.exists() else []
    for cmd in (
        ["uv", "run", "ruff", "check", str(src_dir), "--fix", *cfg],
        ["uv", "run", "ruff", "format", str(src_dir), *cfg],
    ):
        subprocess.run(cmd, cwd=smithy_python, check=True)


if __name__ == "__main__":
    main()
