import os
import sys
import importlib

# Test SYSTEM_ROOT_DIRECTORY
os.environ["SYSTEM_ROOT_DIRECTORY"] = "/Users/konstantin/Programmation/Hackathon/campus-copilot/.cognee_system"
os.environ["DATA_ROOT_DIRECTORY"] = "/Users/konstantin/Programmation/Hackathon/campus-copilot/.cognee_data"

import cognee
print("Path from config:", cognee.config.system_root_directory)
