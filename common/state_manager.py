import os
import json
from typing import TypedDict, Literal, List, Dict, Set, Optional
from pyroute2 import IPRoute
from datetime import datetime

STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "vxlan_bgp_evpn_state.json"
)


class StateManager:
    """状态管理器，用于记录和读取执行状态"""

    @staticmethod
    def load_state() -> Optional[dict]:
        """加载上次执行的状态"""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load state file: {str(e)}")
        return None

    @staticmethod
    def save_state(config: dict, success: bool, operations: dict):
        """保存当前执行状态"""
        state = {
            "timestamp": datetime.now().isoformat(),
            "config": config,
            "success": success,
            "operations": operations,
        }
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save state file: {str(e)}")
