"""`python -m exec_org ...` is the same as the `exec-org` command."""

import sys

from .cli import main

sys.exit(main())
