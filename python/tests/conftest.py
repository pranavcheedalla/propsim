import os
import sys

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "cpp", "build"))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "python"))
sys.path.insert(0, os.path.join(REPOSITORY_ROOT, "data"))
