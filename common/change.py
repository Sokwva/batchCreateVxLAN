from pyroute2 import IPRoute
from common.rollback_manager import RollbackManager
from common.setup import create_veth, assign_ip_address, set_master
from common.query import check_interface_exist
from common.remove import remove_veth


def handle_veth_for_vrf(
    ipr: IPRoute, rollback: RollbackManager, vrf_conf: dict, require_veth: bool
) -> bool:
    """根据InOutVethRequire设置处理veth接口"""
    vrf_name = vrf_conf["VRFName"]
    vrf_in_out_veth_name = vrf_conf.get(
        "VxLANInOutDomainVethPrefix", vrf_conf["VxLANL3VNI"]
    )

    # 先删除现有的veth接口（如果存在）
    in_veth = f"{vrf_in_out_veth_name}-in"
    if check_interface_exist(ipr, in_veth):
        # ext_veth = f"{vrf_in_out_veth_name}-ext"

        if not remove_veth(ipr, rollback, in_veth):
            return False

        # if not remove_veth(ipr, rollback, ext_veth):
        #     return False

    # 如果需要veth接口，则创建并配置
    if require_veth:
        # 创建veth接口
        (in_veth, ext_veth) = create_veth(
            ipr, rollback, f"{vrf_in_out_veth_name}-in", f"{vrf_in_out_veth_name}-ext"
        )
        if not in_veth or not ext_veth:
            return False

        # 分配IP地址
        if not assign_ip_address(ipr, rollback, in_veth, vrf_conf["InVRFVethIPAddr"]):
            return False

        if not assign_ip_address(
            ipr, rollback, ext_veth, vrf_conf["ExternalVRFVethIPAddr"]
        ):
            return False

        # 设置master
        if not set_master(ipr, rollback, in_veth, vrf_name):
            return False

    return True
