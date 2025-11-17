#!/usr/bin/env python3
"""Check installed plugin versions."""

import sys
from acapy_agent.utils.plugin_installer import get_plugin_version, list_plugin_versions


def main():
    """Check plugin versions."""
    if len(sys.argv) < 2:
        print("Usage: python check_plugin_versions.py <plugin_name> [plugin_name2 ...]")
        print("\nExample:")
        print("  python check_plugin_versions.py webvh")
        print("  python check_plugin_versions.py webvh connection_update")
        sys.exit(1)

    plugin_names = sys.argv[1:]
    versions = list_plugin_versions(plugin_names)

    print("Installed plugin versions:")
    print("-" * 50)
    for plugin_name, version in versions.items():
        if version:
            print(f"{plugin_name:30s} {version}")
        else:
            print(f"{plugin_name:30s} (version unknown)")


if __name__ == "__main__":
    main()

