import os
import json
from pyroute2 import IPRoute
from common.types import EnvConf
from common.rollback_manager import RollbackManager
from common.state_manager import StateManager
from distribute.sdr.sdr import configure_vxlan_bgp_evpn_distribute_sdr


if __name__ == "__main__":
    print("Starting VXLAN BGP EVPN configuration...")
    try:
        # 加载配置
        MainEnvConfRaw = os.environ.get("VXLANBGP_MAIN_CONF", "")
        if not MainEnvConfRaw:
            raise ValueError("VXLANBGP_MAIN_CONF environment variable not set")

        MainEnvConf: EnvConf = json.loads(MainEnvConfRaw)

        # 初始化回滚管理器
        rollback = RollbackManager()

        # 加载上次执行状态
        last_state = StateManager.load_state()

        success = False

        match MainEnvConf.get("Mode"):
            case "distribute-symmetric":
                success = configure_vxlan_bgp_evpn_distribute_sdr(MainEnvConf, rollback, last_state)
            case _:
                raise Exception("Imple me")

        # 保存当前状态
        StateManager.save_state(MainEnvConf, success, rollback.operations)

        if success:
            print("Configuration completed successfully.")
        else:
            print("Configuration failed, initiating rollback...")
            with IPRoute() as ipr:
                rollback.rollback(ipr)
            print("Rollback completed.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON configuration")
    except Exception as e:
        print(f"Error: {str(e)}")
        # 如果配置过程中发生异常，也执行回滚
        with IPRoute() as ipr:
            rollback.rollback(ipr)
        print("Rollback completed due to unexpected error.")
