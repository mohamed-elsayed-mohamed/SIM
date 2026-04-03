"""Allow `python -m Build.Python` (e.g. from Docker) without invoking repo-root `build.py`."""

from .pipeline import main

if __name__ == "__main__":
    main()
