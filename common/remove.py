from pyroute2 import IPRoute
from common.rollback_manager import RollbackManager

def remove_vxlan_interface(ipr: IPRoute, rollback: RollbackManager, vni: int) -> bool:
    ifname = f"vxlan{vni}"
    print(f"Removing VXLAN interface {ifname}")
    try:
        idx = ipr.link_lookup(ifname=ifname)
        if idx:
            ipr.link("set", index=idx[0], state="down")
            ipr.link("del", index=idx[0])
            rollback.record_remove_interface(ifname)
            return True
    except Exception as e:
        print(f"Error removing VXLAN interface {ifname}: {str(e)}")
    return False


def remove_bridge(ipr: IPRoute, rollback: RollbackManager, name: str) -> bool:
    print(f"Removing bridge {name}")
    try:
        idx = ipr.link_lookup(ifname=name)
        if idx:
            ipr.link("set", index=idx[0], state="down")
            ipr.link("del", index=idx[0])
            rollback.record_remove_bridge(name)
            return True
    except Exception as e:
        print(f"Error removing bridge {name}: {str(e)}")
    return False


def remove_vlan_interface(
    ipr: IPRoute, rollback: RollbackManager, parent: str, vlan_id: int
) -> bool:
    ifname = f"{parent}.{vlan_id}"
    print(f"Removing VLAN interface {ifname}")
    try:
        idx = ipr.link_lookup(ifname=ifname)
        if idx:
            ipr.link("set", index=idx[0], state="down")
            ipr.link("del", index=idx[0])
            rollback.record_remove_interface(ifname)
            return True
    except Exception as e:
        print(f"Error removing VLAN interface {ifname}: {str(e)}")
    return False


def remove_vrf(ipr: IPRoute, rollback: RollbackManager, name: str) -> bool:
    print(f"Removing VRF {name}")
    try:
        idx = ipr.link_lookup(ifname=name)
        if idx:
            ipr.link("set", index=idx[0], state="down")
            ipr.link("del", index=idx[0])
            rollback.record_remove_vrf(name)
            return True
    except Exception as e:
        print(f"Error removing VRF {name}: {str(e)}")
    return False


def remove_veth(ipr: IPRoute, rollback: RollbackManager, name: str) -> bool:
    print(f"Removing VETH interface {name}")
    try:
        idx = ipr.link_lookup(ifname=name)
        if idx:
            ipr.link("set", index=idx[0], state="down")
            ipr.link("del", index=idx[0])
            rollback.record_remove_veth(name)
            return True
    except Exception as e:
        print(f"Error removing VETH interface {name}: {str(e)}")
    return False


def unassign_ip_address(
    ipr: IPRoute, rollback: RollbackManager, interface: str, ip_addr: str
) -> bool:
    print(f"Removing IP address {ip_addr} from interface {interface}")
    try:
        idx = ipr.link_lookup(ifname=interface)
        if idx:
            ipr.addr(
                "del",
                index=idx[0],
                address=ip_addr.split("/")[0],
                mask=int(ip_addr.split("/")[1]),
            )
            rollback.record_remove_ip_assignment(interface, ip_addr)
            return True
    except Exception as e:
        print(f"Error removing IP {ip_addr} from {interface}: {str(e)}")
    return False


def unset_master(
    ipr: IPRoute, rollback: RollbackManager, slave: str, master: str
) -> bool:
    print(f"Unsetting master {master} for {slave}")
    try:
        idx = ipr.link_lookup(ifname=slave)
        if idx:
            ipr.link("set", index=idx[0], master=0)
            rollback.record_remove_master_relation(slave, master)
            return True
    except Exception as e:
        print(f"Error unsetting master {master} for {slave}: {str(e)}")
    return False
