from pyroute2 import IPRoute


def get_interface_ip(ipr: IPRoute, interface_name: str):
    # 获取接口索引
    interface_index = ipr.link_lookup(ifname=interface_name)
    if not interface_index:
        print(f"Interface {interface_name} not found")
        return None

    # 获取该接口的所有IP地址信息
    addrs = ipr.get_addr(index=interface_index[0])

    # 提取IPv4和IPv6地址
    ipv4_addrs = []
    ipv6_addrs = []

    for addr in addrs:
        attrs = dict(addr["attrs"])
        if "IFA_ADDRESS" in attrs:
            ip = attrs["IFA_ADDRESS"]
            if addr["family"] == 2:  # AF_INET (IPv4)
                ipv4_addrs.append(ip)
            elif addr["family"] == 10:  # AF_INET6 (IPv6)
                ipv6_addrs.append(ip)

    return {"interface": interface_name, "ipv4": ipv4_addrs, "ipv6": ipv6_addrs}


def check_interface_exist(ipr: IPRoute, interface_name: str) -> bool:
    return len(ipr.link_lookup(ifname=interface_name)) != 0
