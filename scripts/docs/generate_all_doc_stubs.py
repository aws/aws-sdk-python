"""
Generate documentation stubs for all AWS SDK Python clients.

This script iterates through each client directory and runs the
generate_doc_stubs.py script with output directed to the top-level docs folder.
It also generates the clients index page.
"""

import logging
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from utils import get_sdk_id

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_all_doc_stubs")

DEFAULT_CPU_COUNT = 1


@dataclass
class ClientInfo:
    """Information about a client for documentation generation."""

    dir: Path
    service_name: str
    package_name: str
    path_name: str


def discover_clients(clients_dir: Path, models_dir: Path) -> list[ClientInfo]:
    """
    Discover all clients that have a generate_doc_stubs.py script.

    Args:
        clients_dir: Path to the clients directory.
        models_dir: Path to the Smithy models directory.

    Returns:
        List of ClientInfo objects.
    """
    if not clients_dir.exists():
        raise FileNotFoundError(f"Clients directory not found: {clients_dir}")

    clients = []
    for client_dir in sorted(clients_dir.iterdir()):
        script_path = client_dir / "scripts" / "docs" / "generate_doc_stubs.py"
        if not script_path.exists():
            continue

        package_name = client_dir.name
        path_name = package_name.replace("aws-sdk-", "")
        service_name = get_sdk_id(models_dir / f"{path_name}.json")
        clients.append(ClientInfo(client_dir, service_name, package_name, path_name))

    return clients


def generate_all_doc_stubs(clients: list[ClientInfo], docs_dir: Path) -> bool:
    """
    Generate doc stubs for all clients by running each client's generate_doc_stubs.py.

    Args:
        clients: List of ClientInfo objects.
        docs_dir: Path to the docs directory.

    Returns:
        True if all doc stubs were generated successfully, False otherwise.
    """
    top_level_docs = docs_dir / "clients"
    max_workers = os.cpu_count() or DEFAULT_CPU_COUNT

    logger.info(
        f"⏳ Generating doc stubs for {len(clients)} clients using {max_workers} workers..."
    )

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _generate_doc_stub,
                client.dir,
                client.service_name,
                top_level_docs / client.path_name,
            ): client
            for client in clients
        }

        failed = []
        for future in as_completed(futures):
            service_name, success = future.result()
            if success:
                logger.info(f"✅ Generated doc stubs for {service_name}")
            else:
                logger.error(f"❌ Failed to generate doc stubs for {service_name}")
                failed.append(service_name)

    if failed:
        logger.error(f"Failed to generate doc stubs for: {', '.join(failed)}")
        return False

    return True


def _generate_doc_stub(
    client_dir: Path, service_name: str, output_dir: Path
) -> tuple[str, bool]:
    """
    Generate doc stubs for a single client.

    Args:
        client_dir: Path to the client directory.
        service_name: Name of the service.
        output_dir: Path to the output directory.

    Returns:
        Tuple of (service_name, success).
    """
    script_path = client_dir / "scripts" / "docs" / "generate_doc_stubs.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--client-dir",
            str(client_dir / "src" / client_dir.name.replace("-", "_")),
            "--output-dir",
            str(output_dir),
            "--service-name",
            service_name,
        ],
        cwd=client_dir,
    )

    return service_name, result.returncode == 0


def generate_clients_index(clients: list[ClientInfo], docs_dir: Path) -> bool:
    """
    Generate clients/index.md (with alphabetical tabs).

    Args:
        clients: List of ClientInfo objects.
        docs_dir: Path to the docs directory.

    Returns:
        True if the index was generated successfully, False otherwise.
    """
    lines = ["# Available Clients", ""]

    # Group by first letter
    grouped: defaultdict[str, list[ClientInfo]] = defaultdict(list)
    for client in clients:
        letter = client.service_name[0].upper()
        grouped[letter].append(client)

    # Tab for all services
    lines.append('=== "All"')
    lines.append("")
    lines.append("    | Service | Package Name |")
    lines.append("    |----------|--------------|")
    for client in clients:
        lines.append(
            f"    | **[{client.service_name}]({client.path_name}/index.md)** | `{client.package_name}` |"
        )
    lines.append("")

    # Individual letter tabs
    for letter in sorted(grouped.keys()):
        lines.append(f'=== "{letter}"')
        lines.append("")
        lines.append("    | Service | Package Name |")
        lines.append("    |----------|--------------|")
        for client in grouped[letter]:
            lines.append(
                f"    | **[{client.service_name}]({client.path_name}/index.md)** | `{client.package_name}` |"
            )
        lines.append("")

    index_path = docs_dir / "clients" / "index.md"
    try:
        index_path.write_text("\n".join(lines) + "\n")
    except OSError as e:
        logger.error(f"Failed to write clients index: {e}")
        return False

    logger.info(f"✅ Generated clients index page with {len(grouped)} letter tabs")
    return True


def main() -> int:
    """Main entry point for generating doc stubs for all clients."""
    repo_root = Path(__file__).parent.parent.parent
    clients_dir = repo_root / "clients"
    docs_dir = repo_root / "docs"
    models_dir = repo_root / "codegen" / "aws-models"

    try:
        clients = discover_clients(clients_dir, models_dir)

        if not generate_all_doc_stubs(clients, docs_dir):
            return 1

        if not generate_clients_index(clients, docs_dir):
            return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
