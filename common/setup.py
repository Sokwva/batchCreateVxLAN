from pyroute2 import IPRoute
from common.rollback_manager import RollbackManager

def create_vxlan_interface(
    ipr: IPRoute, rollback: RollbackManager, vni: int, local_ip: str, group: str = None
) -> str:
    ifname = f"vxlan{vni}"
    print(f"Creating VXLAN interface {ifname} with VNI {vni}")

    try:
        rollback.record_interface(ifname)
        ipr.link(
            "add",
            ifname=ifname,
            kind="vxlan",
            vxlan_id=vni,
            vxlan_local=local_ip,
            vxlan_port=4789,
            vxlan_learning=0,
            vxlan_ttl=64,
        )
        ipr.link("set", index=ipr.link_lookup(ifname=ifname)[0], state="up")
        return ifname
    except Exception as e:
        print(f"Error creating VXLAN interface {ifname}: {str(e)}")
        return ""


def create_bridge(ipr: IPRoute, rollback: RollbackManager, name: str) -> str:
    print(f"Creating bridge {name}")
    try:
        rollback.record_bridge(name)
        ipr.link("add", ifname=name, kind="bridge")
        ipr.link("set", index=ipr.link_lookup(ifname=name)[0], state="up")
        return name
    except Exception as e:
        print(f"Error creating bridge {name}: {str(e)}")
        return ""


def create_vlan_interface(
    ipr: IPRoute, rollback: RollbackManager, parent: str, vlan_id: int
) -> str:
    ifname = f"{parent}.{vlan_id}"
    print(f"Creating VLAN interface {ifname} on {parent}")
    try:
        rollback.record_interface(ifname)
        ipr.link(
            "add",
            ifname=ifname,
            kind="vlan",
            link=ipr.link_lookup(ifname=parent)[0],
            vlan_id=vlan_id,
        )
        ipr.link("set", index=ipr.link_lookup(ifname=ifname)[0], state="up")
        return ifname
    except Exception as e:
        print(f"Error creating VLAN interface {ifname}: {str(e)}")
        return ""


def create_vrf(
    ipr: IPRoute, rollback: RollbackManager, name: str, table_id: int
) -> str:
    print(f"Creating VRF {name} with table ID {table_id}")
    try:
        rollback.record_vrf(name)
        ipr.link("add", ifname=name, kind="vrf", vrf_table=table_id)
        ipr.link("set", index=ipr.link_lookup(ifname=name)[0], state="up")
        return name
    except Exception as e:
        print(f"Error creating VRF {name}: {str(e)}")
        return ""


def create_veth(ipr: IPRoute, rollback: RollbackManager, name: str, peername: str):
    print(f"Creating VETH interface {name}")
    try:
        rollback.record_veth(name)
        ipr.link("add", ifname=name, peer=peername, kind="veth")
        ipr.link("set", index=ipr.link_lookup(ifname=name)[0], state="up")
        ipr.link("set", index=ipr.link_lookup(ifname=peername)[0], state="up")
        return (name, peername)
    except Exception as e:
        print(f"Error creating VETH interface {name}: {str(e)}")
        return ("", "")


def add_interface_to_bridge(
    ipr: IPRoute, rollback: RollbackManager, bridge: str, interface: str
) -> bool:
    print(f"Adding interface {interface} to bridge {bridge}")
    try:
        rollback.record_master_relation(interface, bridge)
        bridge_idx = ipr.link_lookup(ifname=bridge)[0]
        iface_idx = ipr.link_lookup(ifname=interface)[0]
        ipr.link("set", index=iface_idx, master=bridge_idx)
        return True
    except Exception as e:
        print(f"Error adding {interface} to bridge {bridge}: {str(e)}")
        return False


def assign_ip_address(
    ipr: IPRoute, rollback: RollbackManager, interface: str, ip_addr: str
) -> bool:
    print(f"Assigning IP address {ip_addr} to interface {interface}")
    try:
        rollback.record_ip_assignment(interface, ip_addr)
        idx = ipr.link_lookup(ifname=interface)[0]
        ipr.addr(
            "add",
            index=idx,
            address=ip_addr.split("/")[0],
            mask=int(ip_addr.split("/")[1]),
        )
        return True
    except Exception as e:
        print(f"Error assigning IP {ip_addr} to {interface}: {str(e)}")
        return False


def set_mac_address(
    ipr: IPRoute, rollback: RollbackManager, interface: str, mac_addr: str
) -> bool:
    print(f"Setting MAC address {mac_addr} for interface {interface}")
    try:
        idx = ipr.link_lookup(ifname=interface)[0]
        ipr.link("set", index=idx, address=mac_addr)
        return True
    except Exception as e:
        print(f"Error setting MAC address for {interface}: {str(e)}")
        return False


def set_master(
    ipr: IPRoute, rollback: RollbackManager, interface: str, master: str
) -> bool:
    print(f"Setting {interface} master to {master}")
    try:
        rollback.record_master_relation(interface, master)
        iface_idx = ipr.link_lookup(ifname=interface)[0]
        master_idx = ipr.link_lookup(ifname=master)[0]
        ipr.link("set", index=iface_idx, master=master_idx)
        return True
    except Exception as e:
        print(f"Error setting {interface} master to {master}: {str(e)}")
        return False
