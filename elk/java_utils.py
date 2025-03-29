#!/usr/bin/env python3
"""Utilities for managing the ELK server distribution."""

import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path

import pooch

# Constants
JAVA_MIN_VERSION = 17
JAVA_MAX_VERSION = 23

# Configuration for the ELK server
ELK_SERVER_VERSION = "0.2.0"
ZIP_FILENAME = f"elk-server-{ELK_SERVER_VERSION}.zip"
ZIP_URL = f"https://github.com/TypeFox/elk-server/releases/download/v{ELK_SERVER_VERSION}/{ZIP_FILENAME}"


def get_java_version(java_path: str) -> int:
    """
    Get the major version of Java from the given path.

    Args:
        java_path: Path to the Java executable

    Returns:
        int: The major version number

    Raises:
        RuntimeError: If Java version cannot be determined
    """
    try:
        result = subprocess.run(
            [java_path, "-version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version_str = result.stderr.split("\n")[0]
        # Extract major version number
        version = version_str.split('"')[1].split(".")[0]
        if version.startswith("1."):  # Old style version (1.8)
            version = version_str.split('"')[1].split(".")[1]
        return int(version)
    except (subprocess.CalledProcessError, IndexError, ValueError) as err:
        raise RuntimeError(f"Failed to determine Java version: {err}") from err


def find_java() -> str:
    """
    Find a suitable Java installation.

    Returns:
        str: Path to Java executable

    Raises:
        RuntimeError: If no suitable Java installation is found
    """
    # Check JAVA_HOME first
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        java_exe = "java.exe" if platform.system() == "Windows" else "java"
        java_path = os.path.join(java_home, "bin", java_exe)
        if os.path.isfile(java_path):
            try:
                version = get_java_version(java_path)
                if JAVA_MIN_VERSION <= version <= JAVA_MAX_VERSION:
                    return java_path
            except RuntimeError as err:
                raise RuntimeError("Failed to check Java version in JAVA_HOME") from err

    # Try java from PATH
    java_cmd = shutil.which("java")
    if java_cmd:
        try:
            version = get_java_version(java_cmd)
            if JAVA_MIN_VERSION <= version <= JAVA_MAX_VERSION:
                return java_cmd
        except RuntimeError as err:
            raise RuntimeError("Failed to check Java version in PATH") from err

    raise RuntimeError(
        f"No Java {JAVA_MIN_VERSION}-{JAVA_MAX_VERSION} installation found. "
        "Please install Java or set JAVA_HOME."
    )


def get_cache_dir() -> Path:
    """
    Get the cache directory for storing the ELK server distribution.

    Returns:
        Path: The cache directory path
    """
    return Path.home() / ".cache" / "elk-server"


def extract_distribution(zip_path: str, cache_dir: str) -> str:
    """
    Extract the ELK server distribution.

    Args:
        zip_path: Path to the downloaded zip file
        cache_dir: Directory to extract to

    Returns:
        str: Path to the server script
    """
    try:
        server_dir = Path(cache_dir) / f"elk-server-{ELK_SERVER_VERSION}"
        script_path = server_dir / "bin" / "elk-server"

        # Only extract if the script doesn't exist
        if not script_path.exists():
            # Remove old directory if it exists
            if server_dir.exists():
                shutil.rmtree(server_dir)

            # Extract everything
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(cache_dir)

            # Make the script executable
            script_path.chmod(0o755)

        return str(script_path)
    except Exception as err:
        raise RuntimeError(f"Failed to extract ELK server distribution: {err}") from err


# Create a pooch to manage downloading the server
server_manager = pooch.create(
    path=get_cache_dir(),
    base_url="https://github.com/TypeFox/elk-server/releases/download/",
    registry={
        ZIP_FILENAME: None,  # We'll update the hash when we know it
    },
    urls={
        ZIP_FILENAME: ZIP_URL,
    },
)


def ensure_server() -> Path:
    """
    Ensure the ELK server distribution is available and return path to the script.

    Returns:
        Path: The path to the server script
    """
    try:
        # Find Java first - this will raise if Java is not available
        find_java()

        # Download the zip file
        zip_path = server_manager.fetch(ZIP_FILENAME)

        # Extract the distribution
        script_path = extract_distribution(
            zip_path=zip_path, cache_dir=str(get_cache_dir())
        )

        return Path(script_path)
    except Exception as err:
        raise RuntimeError("Failed to ensure ELK server is available") from err
