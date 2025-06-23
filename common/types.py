from typing import TypedDict, Literal


# 定义类型提示
class VlanMapVNIList(TypedDict):
    VlanID: int
    L2VxLANVNI: int
    L2VxLANVNIIPAddr: str
    L2VxLANVNIMacAddr: str
    L3VxLANVNI: int


class VRFMapL3VNIList(TypedDict):
    VRFName: str
    VxLANL3VNI: int
    VRFRouteTableID: int
    VxLANInOutDomainVethPrefix: str
    InOutVethRequire: bool
    InVRFVethIPAddr: str
    ExternalVRFVethIPAddr: str


class EnvConf(TypedDict):
    Mode: Literal["central", "distribute-asymmetric", "distribute-symmetric"]
    VlanMapVNI: list[VlanMapVNIList]
    VRFMapL3VNI: list[VRFMapL3VNIList]
    UnderlayEth: str
    OverlayEth: str


def validate_config(conf: EnvConf) -> bool:
    """验证配置的完整性"""
    # 检查Mode字段
    if conf.get("Mode") not in [
        "central",
        "distribute-asymmetric",
        "distribute-symmetric",
    ]:
        print("Error: Invalid or missing 'Mode' in configuration")
        return False

    # 检查Underlay和Overlay接口
    if not conf.get("UnderlayEth"):
        print("Error: 'UnderlayEth' is required in configuration")
        return False

    if not conf.get("OverlayEth"):
        print("Error: 'OverlayEth' is required in configuration")
        return False

    # 检查VlanMapVNI
    if not conf.get("VlanMapVNI") or not isinstance(conf["VlanMapVNI"], list):
        print("Error: 'VlanMapVNI' must be a non-empty list")
        return False

    for vlan_conf in conf["VlanMapVNI"]:
        if not all(
            key in vlan_conf
            for key in [
                "VlanID",
                "L2VxLANVNI",
                "L2VxLANVNIIPAddr",
                "L2VxLANVNIMacAddr",
                "L3VxLANVNI",
            ]
        ):
            print("Error: Missing required fields in VlanMapVNI configuration")
            return False

        if not (1 <= vlan_conf["VlanID"] <= 4094):
            print(f"Error: Invalid VlanID {vlan_conf['VlanID']} (must be 1-4094)")
            return False

        if not (1 <= vlan_conf["L2VxLANVNI"] <= 16777215):
            print(
                f"Error: Invalid L2VxLANVNI {vlan_conf['L2VxLANVNI']} (must be 1-16777215)"
            )
            return False

        if not (1 <= vlan_conf["L3VxLANVNI"] <= 16777215):
            print(
                f"Error: Invalid L3VxLANVNI {vlan_conf['L3VxLANVNI']} (must be 1-16777215)"
            )
            return False

        if (
            not vlan_conf["L2VxLANVNIIPAddr"]
            or "/" not in vlan_conf["L2VxLANVNIIPAddr"]
        ):
            print(f"Error: Invalid L2VxLANVNIIPAddr {vlan_conf['L2VxLANVNIIPAddr']}")
            return False

        if (
            not vlan_conf["L2VxLANVNIMacAddr"]
            or len(vlan_conf["L2VxLANVNIMacAddr"].split(":")) != 6
        ):
            print(f"Error: Invalid L2VxLANVNIMacAddr {vlan_conf['L2VxLANVNIMacAddr']}")
            return False

    # 检查VRFMapL3VNI
    if not conf.get("VRFMapL3VNI") or not isinstance(conf["VRFMapL3VNI"], list):
        print("Error: 'VRFMapL3VNI' must be a non-empty list")
        return False

    for vrf_conf in conf["VRFMapL3VNI"]:
        if not all(
            key in vrf_conf
            for key in [
                "VRFName",
                "VxLANL3VNI",
                "VRFRouteTableID",
                "VxLANInOutDomainVethPrefix",
                "InOutVethRequire",
                "InVRFVethIPAddr",
                "ExternalVRFVethIPAddr",
            ]
        ):
            print("Error: Missing required fields in VRFMapL3VNI configuration")
            return False

        if not vrf_conf["VRFName"]:
            print("Error: VRFName cannot be empty")
            return False

        if type(vrf_conf["InOutVethRequire"]) is not bool:
            print("Error: InOutVethRequire cannot be empty")
            return False

        if not (1 <= vrf_conf["VxLANL3VNI"] <= 16777215):
            print(
                f"Error: Invalid VxLANL3VNI {vrf_conf['VxLANL3VNI']} (must be 1-16777215)"
            )
            return False

        if not vrf_conf["InVRFVethIPAddr"] or "/" not in vrf_conf["InVRFVethIPAddr"]:
            print(f"Error: Invalid InVRFVethIPAddr {vrf_conf['InVRFVethIPAddr']}")
            return False

        if (
            not vrf_conf["ExternalVRFVethIPAddr"]
            or "/" not in vrf_conf["ExternalVRFVethIPAddr"]
        ):
            print(
                f"Error: Invalid ExternalVRFVethIPAddr {vrf_conf['ExternalVRFVethIPAddr']}"
            )
            return False

    return True
