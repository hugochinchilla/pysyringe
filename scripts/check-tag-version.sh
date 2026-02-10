#!/usr/bin/env bash
# Validates that a version tag matches __version__ in pysyringe/__init__.py.
# Used as a pre-push hook to prevent pushing tags that don't match the code.
#
# As a pre-push hook, git passes the remote name and URL as arguments and
# feeds pushed refs on stdin.  We inspect each ref for version tags (v*).

set -euo pipefail

INIT_FILE="pysyringe/__init__.py"

code_version=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$INIT_FILE")

if [ -z "$code_version" ]; then
    echo "ERROR: Could not read __version__ from $INIT_FILE"
    exit 1
fi

while read -r local_ref local_oid remote_ref remote_oid; do
    # Only check version tags (refs/tags/v*)
    case "$remote_ref" in
        refs/tags/v*)
            tag_version="${remote_ref#refs/tags/v}"
            if [ "$tag_version" != "$code_version" ]; then
                echo "ERROR: Tag v${tag_version} does not match __version__ = \"${code_version}\" in $INIT_FILE"
                echo "       Update __version__ or use the correct tag."
                exit 1
            fi
            echo "OK: Tag v${tag_version} matches __version__"
            ;;
    esac
done

exit 0
