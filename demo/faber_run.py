"""
faber demo run glue
"""

import os
import sys
import asyncio

#  append parent directory to path to find demo package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from  demo.faberfix import main

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        os._exit(1)


