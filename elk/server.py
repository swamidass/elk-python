#!/usr/bin/env python3
"""ELK server runner module."""

import json
import subprocess
import sys
from typing import Optional

from pydantic import validate_call

from .java_utils import ensure_server
from .types import ElkGraph

# Global server process
_server_process: Optional[subprocess.Popen] = None


def _ensure_server_process() -> subprocess.Popen:
    """
    Ensure a server process is running and return it.
    Creates a new process if none exists or if the existing one has terminated.

    Returns:
        subprocess.Popen: The server process

    Raises:
        RuntimeError: If the server process cannot be created
    """
    global _server_process

    # Check if we need to create a new process
    if _server_process is None or _server_process.poll() is not None:
        # Get the path to the ELK server script
        server_script = ensure_server()

        # Start the server process
        _server_process = subprocess.Popen(
            [server_script, "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        if (
            _server_process.stdin is None
            or _server_process.stdout is None
            or _server_process.stderr is None
        ):
            raise RuntimeError("Failed to open subprocess pipes")

    return _server_process


def run_elk_server(mode="stdio"):
    """
    Run the ELK server.

    Args:
        mode (str): Either 'stdio' or 'socket'
    """
    if mode not in ["stdio", "socket"]:
        print(f"Invalid mode: {mode}. Must be 'stdio' or 'socket'", file=sys.stderr)
        sys.exit(1)

    # Get the path to the ELK server script
    server_script = ensure_server()

    # Initialize jenv and run the server
    cmd = f"{server_script} --{mode}"

    print(f"Running ELK server in {mode} mode...", file=sys.stderr)
    print(f"Command: {cmd}", file=sys.stderr)

    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE if mode == "stdio" else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This is preferred over universal_newlines
            bufsize=1,  # Line buffered
        )

        if process.stdout is None or process.stderr is None:
            raise RuntimeError("Failed to open subprocess pipes")

        print("\nServer output:", file=sys.stderr)

        # In stdio mode, we need to pass through stdin to the process
        if mode == "stdio" and process.stdin is not None:
            # Process each line of input as a separate JSON message
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                # Send the JSON message
                process.stdin.write(line + "\n")
                process.stdin.flush()

                # Read the response
                response = process.stdout.readline()
                if response:
                    print(response.strip())

                # Check for errors
                error = process.stderr.readline()
                if error:
                    print(f"Error: {error.strip()}", file=sys.stderr)

            # Close stdin to signal we're done
            process.stdin.close()

        # Handle any remaining output
        while process.poll() is None:
            # Read stdout
            try:
                line = process.stdout.readline()
                if line:
                    if mode == "stdio":
                        print(line.strip())
                    else:
                        print(line.strip(), file=sys.stderr)
            except Exception as err:  # Changed from bare except
                print(f"Error reading stdout: {err}", file=sys.stderr)

            # Read stderr
            try:
                error = process.stderr.readline()
                if error:
                    print(f"Error: {error.strip()}", file=sys.stderr)
            except Exception as err:  # Changed from bare except
                print(f"Error reading stderr: {err}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nStopping ELK server...", file=sys.stderr)
        if process.stdin is not None:
            process.stdin.close()
        process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"Error running ELK server: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Make sure the process is terminated
        try:
            process.terminate()
        except Exception as err:  # Changed from bare except
            print(f"Error terminating process: {err}", file=sys.stderr)


def main():
    """Command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run the ELK layout server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "socket"],
        default="stdio",
        help="Server mode (default: stdio)",
    )

    args = parser.parse_args()
    run_elk_server(args.mode)


@validate_call()
def compute_layout(graph: dict | ElkGraph) -> dict:
    """
    Compute a layout for the given graph using the ELK server.
    Reuses a single server process across multiple calls.

    Args:
        graph: The graph to be laid out, either as a dictionary or ElkGraph model

    Returns:
        dict: The computed layout from ELK

    Raises:
        RuntimeError: If the server fails or returns an error
        ValidationError: If the input validation fails
        json.JSONDecodeError: If the response cannot be parsed
    """
    # Get or create the server process
    process: subprocess.Popen = _ensure_server_process()

    if process.stdin is None or process.stdout is None or process.stderr is None:
        raise RuntimeError("Server process has invalid pipes")

    try:
        # Always validate through ElkGraph
        validated_graph: ElkGraph = (
            graph if isinstance(graph, ElkGraph) else ElkGraph(**graph)
        )

        # Send the JSON data without null values
        json_str: str = validated_graph.model_dump_json(exclude_none=True)
        process.stdin.write(json_str + "\n")
        process.stdin.flush()

        # Read the response
        response: str = process.stdout.readline()
        if not response:
            # Check for errors
            error: str = process.stderr.read()
            raise RuntimeError(f"ELK server failed: {error}")

        # Check for errors
        error = process.stderr.readline()
        if error:
            error = error.strip()
            # Only raise if it's not the expected EOF error after successful layout
            if not error.endswith("End of input at line 2 column 1 path $"):
                raise RuntimeError(f"ELK server error: {error}") from None

        # Parse the response
        return json.loads(response)

    except (OSError, BrokenPipeError) as e:
        # Server crashed or disconnected - clear the global process
        global _server_process
        _server_process = None
        raise RuntimeError(f"ELK server connection failed: {e}") from e


def shutdown_server():
    """Shutdown the ELK server process if it's running."""
    global _server_process
    if _server_process is not None:
        try:
            if _server_process.stdin:
                _server_process.stdin.close()
            _server_process.terminate()
            _server_process.wait(timeout=1)
        except Exception as err:  # Changed from bare except
            print(f"Error shutting down server: {err}", file=sys.stderr)
        finally:
            _server_process = None


if __name__ == "__main__":
    main()
