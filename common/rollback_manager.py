import os
import json
from typing import TypedDict, Literal, List, Dict, Set, Optional
from pyroute2 import IPRoute
from datetime import datetime


class RollbackManager:
    """增强的回滚管理器，支持增量操作"""

    def __init__(self):
        self.created_interfaces: Set[str] = set()
        self.created_bridges: Set[str] = set()
        self.created_vrfs: Set[str] = set()
        self.created_veths: Set[str] = set()
        self.assigned_ips: Dict[str, List[str]] = {}
        self.master_relations: Dict[str, str] = {}
        self.operations: Dict[str, List[dict]] = {
            "interfaces": [],
            "bridges": [],
            "vrfs": [],
            "veths": [],
            "ip_assignments": [],
            "master_relations": [],
        }

    def record_interface(
        self, ifname: str, vni: Optional[int] = None, vlan_id: Optional[int] = None
    ):
        self.created_interfaces.add(ifname)
        self.operations["interfaces"].append(
            {"name": ifname, "vni": vni, "vlan_id": vlan_id, "action": "add"}
        )

    def record_bridge(self, brname: str, vni: Optional[int] = None):
        self.created_bridges.add(brname)
        self.operations["bridges"].append({"name": brname, "vni": vni, "action": "add"})

    def record_vrf(self, vrfname: str, vni: Optional[int] = None):
        self.created_vrfs.add(vrfname)
        self.operations["vrfs"].append({"name": vrfname, "vni": vni, "action": "add"})

    def record_veth(self, vethname: str, vrf: Optional[str] = None):
        self.created_veths.add(vethname)
        self.operations["veths"].append({"name": vethname, "vrf": vrf, "action": "add"})

    def record_ip_assignment(self, ifname: str, ip: str):
        if ifname not in self.assigned_ips:
            self.assigned_ips[ifname] = []
        self.assigned_ips[ifname].append(ip)
        self.operations["ip_assignments"].append(
            {"interface": ifname, "ip": ip, "action": "add"}
        )

    def record_master_relation(self, slave: str, master: str):
        self.master_relations[slave] = master
        self.operations["master_relations"].append(
            {"slave": slave, "master": master, "action": "add"}
        )

    def record_remove_interface(self, ifname: str):
        self.operations["interfaces"].append({"name": ifname, "action": "del"})

    def record_remove_bridge(self, brname: str):
        self.operations["bridges"].append({"name": brname, "action": "del"})

    def record_remove_vrf(self, vrfname: str):
        self.operations["vrfs"].append({"name": vrfname, "action": "del"})

    def record_remove_veth(self, vethname: str):
        self.operations["veths"].append({"name": vethname, "action": "del"})

    def record_remove_ip_assignment(self, ifname: str, ip: str):
        self.operations["ip_assignments"].append(
            {"interface": ifname, "ip": ip, "action": "del"}
        )

    def record_remove_master_relation(self, slave: str, master: str):
        self.operations["master_relations"].append(
            {"slave": slave, "master": master, "action": "del"}
        )

    def rollback(self, ipr: IPRoute):
        """执行回滚操作"""
        print("Starting rollback...")

        # 1. 解除master关系
        for slave, master in self.master_relations.items():
            try:
                idx = ipr.link_lookup(ifname=slave)
                if idx:
                    ipr.link("set", index=idx[0], state="down")
                    ipr.link("set", index=idx[0], master=0)
                    print(f"Rollback: Unset master for {slave}")
            except Exception as e:
                print(f"Rollback error unsetting master for {slave}: {str(e)}")

        # 2. 删除分配的IP地址
        for ifname, ips in self.assigned_ips.items():
            for ip in ips:
                try:
                    idx = ipr.link_lookup(ifname=ifname)
                    if idx:
                        ipr.addr(
                            "del",
                            index=idx[0],
                            address=ip.split("/")[0],
                            mask=int(ip.split("/")[1]),
                        )
                        print(f"Rollback: Removed IP {ip} from {ifname}")
                except Exception as e:
                    print(f"Rollback error removing IP {ip} from {ifname}: {str(e)}")

        # 3. 删除VETH接口
        for veth in self.created_veths:
            try:
                idx = ipr.link_lookup(ifname=veth)
                if idx:
                    ipr.link("del", index=idx[0])
                    print(f"Rollback: Deleted VETH interface {veth}")
            except Exception as e:
                print(f"Rollback error deleting VETH {veth}: {str(e)}")

        # 4. 删除桥接接口
        for br in self.created_bridges:
            try:
                idx = ipr.link_lookup(ifname=br)
                if idx:
                    ipr.link("del", index=idx[0])
                    print(f"Rollback: Deleted bridge {br}")
            except Exception as e:
                print(f"Rollback error deleting bridge {br}: {str(e)}")

        # 5. 删除VXLAN/VLAN接口
        for iface in self.created_interfaces:
            try:
                idx = ipr.link_lookup(ifname=iface)
                if idx:
                    ipr.link("del", index=idx[0])
                    print(f"Rollback: Deleted interface {iface}")
            except Exception as e:
                print(f"Rollback error deleting interface {iface}: {str(e)}")

        # 6. 删除VRF
        for vrf in self.created_vrfs:
            try:
                idx = ipr.link_lookup(ifname=vrf)
                if idx:
                    ipr.link("del", index=idx[0])
                    print(f"Rollback: Deleted VRF {vrf}")
            except Exception as e:
                print(f"Rollback error deleting VRF {vrf}: {str(e)}")

        print("Rollback completed.")
