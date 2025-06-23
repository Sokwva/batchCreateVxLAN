from typing import Optional
from pyroute2 import IPRoute
from common.types import EnvConf, validate_config
from common.rollback_manager import RollbackManager
from common.query import get_interface_ip
from common.diff_analyzer import DiffAnalyzer
from common.setup import (
    create_bridge,
    create_veth,
    create_vlan_interface,
    create_vrf,
    create_vxlan_interface,
    set_mac_address,
    set_master,
    add_interface_to_bridge,
    assign_ip_address,
)
from common.change import handle_veth_for_vrf
from common.remove import (
    remove_bridge,
    remove_veth,
    remove_vlan_interface,
    remove_vrf,
    remove_vxlan_interface,
    unassign_ip_address,
    unset_master,
)


def configure_vxlan_bgp_evpn_distribute_sdr(
    conf: EnvConf, rollback: RollbackManager, last_state: Optional[dict] = None
) -> bool:
    """支持增量操作的主配置函数"""
    ipr = IPRoute()

    try:
        # 验证配置
        if not validate_config(conf):
            print("Configuration validation failed")
            return False

        # 检查物理接口
        underlay_index = ipr.link_lookup(ifname=conf["UnderlayEth"])
        if not underlay_index:
            print(f"Error: Underlay interface {conf['UnderlayEth']} not found")
            return False

        overlay_index = ipr.link_lookup(ifname=conf["OverlayEth"])
        if not overlay_index:
            print(f"Error: Overlay interface {conf['OverlayEth']} not found")
            return False

        # 获取Underlay IP
        underlayEthIPAddr = get_interface_ip(ipr, conf["UnderlayEth"])
        if not underlayEthIPAddr or not underlayEthIPAddr.get("ipv4"):
            print(
                f"Error: Underlay interface {conf['UnderlayEth']} has no IPv4 address"
            )
            return False

        underlay_ip = underlayEthIPAddr["ipv4"][0]
        if not underlay_ip:
            print("Error: Underlay interface IP address is empty")
            return False

        # 如果有上次的状态，计算差异并执行增量操作
        if last_state and last_state.get("success", False):
            last_config = last_state.get("config", {})

            # 比较VRF配置差异
            vrf_diff = DiffAnalyzer.compare_vrf_config_with_details(
                last_config.get("VRFMapL3VNI", []), conf.get("VRFMapL3VNI", [])
            )

            # 处理删除的VRF
            for vrf_conf in vrf_diff["removed"]:
                vrf_name = vrf_conf["VRFName"]
                l3_vni = vrf_conf["VxLANL3VNI"]
                vrf_in_out_veth_name = vrf_conf.get(
                    "VxLANInOutDomainVethPrefix", l3_vni
                )

                # 删除相关资源
                l3_br_name = f"br-vsi{l3_vni}"
                l3_vxlan_ifname = f"vxlan{l3_vni}"

                # 删除veth接口
                if vrf_conf.get("InOutVethRequire", False) and not remove_veth(
                    ipr, rollback, f"{vrf_in_out_veth_name}-in"
                ):
                    return False

                # if not remove_veth(ipr, rollback, f"{vrf_in_out_veth_name}-ext"):
                #     return False

                # 解除桥接master关系
                if not unset_master(ipr, rollback, l3_br_name, vrf_name):
                    return False

                # 删除桥接
                if not remove_bridge(ipr, rollback, l3_br_name):
                    return False

                # 删除VXLAN接口
                if not remove_vxlan_interface(ipr, rollback, l3_vni):
                    return False

                # 删除VRF
                if not remove_vrf(ipr, rollback, vrf_name):
                    return False

            # 处理新增和修改的VRF
            for vrf_change_info in vrf_diff["changed"]:
                vrf_conf = vrf_change_info["new"]
                vrf_name = vrf_conf["VRFName"]
                l3_vni = vrf_conf["VxLANL3VNI"]
                vrf_table_id = vrf_conf.get("VRFRouteTableID", l3_vni)
                vrf_in_out_veth_name = vrf_conf.get(
                    "VxLANInOutDomainVethPrefix", l3_vni
                )
                require_veth = vrf_conf.get("InOutVethRequire", False)

                # 创建/更新vrf
                if any(key in vrf_change_info["changed_fields"] for key in ["VRFName","VRFRouteTableID"]):
                    if not create_vrf(ipr, rollback, vrf_name, vrf_table_id):
                        return False

                # 创建/更新L3 
                if "VxLANL3VNI" in vrf_change_info["changed_fields"]:
                    l3_vxlan_ifname = create_vxlan_interface(
                        ipr, rollback, l3_vni, underlay_ip
                    )
                    if not l3_vxlan_ifname:
                        return False

                    # 创建/更新L3桥接
                    l3_br_name = f"br-vsi{l3_vni}"
                    if not create_bridge(ipr, rollback, l3_br_name):
                        return False

                    # 添加接口到桥接
                    if not add_interface_to_bridge(
                        ipr, rollback, l3_br_name, l3_vxlan_ifname
                    ):
                        return False

                    # 设置桥接master
                    if not set_master(ipr, rollback, l3_br_name, vrf_name):
                        return False

                # 创建/更新veth接口
                if "InOutVethRequire" in vrf_change_info["changed_fields"]:
                    if not handle_veth_for_vrf(ipr, rollback, vrf_conf, require_veth):
                        return False

            # 比较VLAN配置差异
            vlan_diff = DiffAnalyzer.compare_vlan_config(
                last_config.get("VlanMapVNI", []), conf.get("VlanMapVNI", [])
            )

            # 处理删除的VLAN配置
            for vlan_conf in vlan_diff["removed"]:
                vlan_id = vlan_conf["VlanID"]
                l2_vni = vlan_conf["L2VxLANVNI"]
                l3_vni = vlan_conf["L3VxLANVNI"]

                # 查找VRF
                vrf_conf = next(
                    (v for v in conf["VRFMapL3VNI"] if v["VxLANL3VNI"] == l3_vni), None
                )
                if not vrf_conf:
                    print(f"Error: No VRF configuration found for L3 VNI {l3_vni}")
                    return False

                vrf_name = vrf_conf["VRFName"]
                l2_br_name = f"br-vsi{l2_vni}"
                l2_vxlan_ifname = f"vxlan{l2_vni}"
                vlan_ifname = f"{conf['OverlayEth']}.{vlan_id}"

                # 解除桥接master关系
                if not unset_master(ipr, rollback, l2_br_name, vrf_name):
                    return False

                # 删除IP地址
                if not unassign_ip_address(
                    ipr, rollback, l2_br_name, vlan_conf["L2VxLANVNIIPAddr"]
                ):
                    return False

                # 删除桥接
                if not remove_bridge(ipr, rollback, l2_br_name):
                    return False

                # 删除VXLAN接口
                if not remove_vxlan_interface(ipr, rollback, l2_vni):
                    return False

                # 删除VLAN接口
                if not remove_vlan_interface(
                    ipr, rollback, conf["OverlayEth"], vlan_id
                ):
                    return False

            # 处理新增和修改的VLAN配置
            for vlan_conf in vlan_diff["added"] + vlan_diff["changed"]:
                vlan_id = vlan_conf["VlanID"]
                l2_vni = vlan_conf["L2VxLANVNI"]
                l3_vni = vlan_conf["L3VxLANVNI"]

                # 查找VRF
                vrf_conf = next(
                    (v for v in conf["VRFMapL3VNI"] if v["VxLANL3VNI"] == l3_vni), None
                )
                if not vrf_conf:
                    print(f"Error: No VRF configuration found for L3 VNI {l3_vni}")
                    return False

                vrf_name = vrf_conf["VRFName"]

                # 创建/更新L2 VXLAN
                l2_vxlan_ifname = create_vxlan_interface(
                    ipr, rollback, l2_vni, underlay_ip
                )
                if not l2_vxlan_ifname:
                    return False

                # 创建/更新VLAN接口
                vlan_ifname = create_vlan_interface(
                    ipr, rollback, conf["OverlayEth"], vlan_id
                )
                if not vlan_ifname:
                    return False

                # 创建/更新L2桥接
                l2_br_name = f"br-vsi{l2_vni}"
                if not create_bridge(ipr, rollback, l2_br_name):
                    return False

                # 设置MAC和IP
                if not set_mac_address(
                    ipr, rollback, l2_br_name, vlan_conf["L2VxLANVNIMacAddr"]
                ):
                    return False

                if not assign_ip_address(
                    ipr, rollback, l2_br_name, vlan_conf["L2VxLANVNIIPAddr"]
                ):
                    return False

                # 添加接口到桥接
                if not add_interface_to_bridge(
                    ipr, rollback, l2_br_name, l2_vxlan_ifname
                ):
                    return False

                if not add_interface_to_bridge(ipr, rollback, l2_br_name, vlan_ifname):
                    return False

                # 设置桥接master
                if not set_master(ipr, rollback, l2_br_name, vrf_name):
                    return False
        else:
            # 处理VRF配置
            for vrf_conf in conf["VRFMapL3VNI"]:
                vrf_name = vrf_conf["VRFName"]
                l3_vni = vrf_conf["VxLANL3VNI"]
                vrf_table_id = vrf_conf.get("VRFRouteTableID", l3_vni)
                vrf_in_out_veth_name = vrf_conf.get(
                    "VxLANInOutDomainVethPrefix", l3_vni
                )

                # 创建VRF
                if not create_vrf(ipr, rollback, vrf_name, vrf_table_id):
                    return False

                # 创建L3 VXLAN
                l3_vxlan_ifname = create_vxlan_interface(
                    ipr, rollback, l3_vni, underlay_ip
                )
                if not l3_vxlan_ifname:
                    return False

                # 创建L3桥接
                l3_br_name = f"br-vsi{l3_vni}"
                if not create_bridge(ipr, rollback, l3_br_name):
                    return False

                # 添加接口到桥接
                if not add_interface_to_bridge(
                    ipr, rollback, l3_br_name, l3_vxlan_ifname
                ):
                    return False

                # 设置桥接master
                if not set_master(ipr, rollback, l3_br_name, vrf_name):
                    return False

                # 创建veth接口
                if vrf_conf.get("InOutVethRequire", False):
                    (in_veth, ext_veth) = create_veth(
                        ipr,
                        rollback,
                        f"{vrf_in_out_veth_name}-in",
                        f"{vrf_in_out_veth_name}-ext",
                    )
                    if not in_veth:
                        return False

                    if not ext_veth:
                        return False

                    # 分配IP地址
                    if not assign_ip_address(
                        ipr, rollback, in_veth, vrf_conf["InVRFVethIPAddr"]
                    ):
                        return False

                    if not assign_ip_address(
                        ipr, rollback, ext_veth, vrf_conf["ExternalVRFVethIPAddr"]
                    ):
                        return False

                    # 设置master
                    if not set_master(ipr, rollback, in_veth, vrf_name):
                        return False

            # 处理VLAN到VNI映射
            for vlan_conf in conf["VlanMapVNI"]:
                vlan_id = vlan_conf["VlanID"]
                l2_vni = vlan_conf["L2VxLANVNI"]
                l3_vni = vlan_conf["L3VxLANVNI"]

                # 查找VRF
                vrf_conf = next(
                    (v for v in conf["VRFMapL3VNI"] if v["VxLANL3VNI"] == l3_vni), None
                )
                if not vrf_conf:
                    print(f"Error: No VRF configuration found for L3 VNI {l3_vni}")
                    return False

                vrf_name = vrf_conf["VRFName"]

                # 创建L2 VXLAN
                l2_vxlan_ifname = create_vxlan_interface(
                    ipr, rollback, l2_vni, underlay_ip
                )
                if not l2_vxlan_ifname:
                    return False

                # 创建VLAN接口
                vlan_ifname = create_vlan_interface(
                    ipr, rollback, conf["OverlayEth"], vlan_id
                )
                if not vlan_ifname:
                    return False

                # 创建L2桥接
                l2_br_name = f"br-vsi{l2_vni}"
                if not create_bridge(ipr, rollback, l2_br_name):
                    return False

                # 设置MAC和IP
                if not set_mac_address(
                    ipr, rollback, l2_br_name, vlan_conf["L2VxLANVNIMacAddr"]
                ):
                    return False

                if not assign_ip_address(
                    ipr, rollback, l2_br_name, vlan_conf["L2VxLANVNIIPAddr"]
                ):
                    return False

                # 添加接口到桥接
                if not add_interface_to_bridge(
                    ipr, rollback, l2_br_name, l2_vxlan_ifname
                ):
                    return False

                if not add_interface_to_bridge(ipr, rollback, l2_br_name, vlan_ifname):
                    return False

                # 设置桥接master
                if not set_master(ipr, rollback, l2_br_name, vrf_name):
                    return False

        return True

    except Exception as e:
        print(f"Error during configuration: {str(e)}")
        return False
    finally:
        ipr.close()
