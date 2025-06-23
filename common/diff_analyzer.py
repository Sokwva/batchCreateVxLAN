from common.types import VRFMapL3VNIList,VlanMapVNIList


class DiffAnalyzer:
    """差异分析器，用于比较新旧配置"""

    @staticmethod
    def compare_vlan_config(old: list[VlanMapVNIList], new: list[VlanMapVNIList]) -> dict:
        """比较VLAN配置差异"""
        old_map = {v["VlanID"]: v for v in old}
        new_map = {v["VlanID"]: v for v in new}

        added = [v for vid, v in new_map.items() if vid not in old_map]
        removed = [v for vid, v in old_map.items() if vid not in new_map]
        changed = []

        for vid in set(old_map.keys()) & set(new_map.keys()):
            if old_map[vid] != new_map[vid]:
                changed.append(new_map[vid])

        return {"added": added, "removed": removed, "changed": changed}

    @staticmethod
    def compare_vrf_config(old: list[VRFMapL3VNIList], new: list[VRFMapL3VNIList]) -> dict:
        """比较VRF配置差异"""
        old_map = {v["VRFName"]: v for v in old}
        new_map = {v["VRFName"]: v for v in new}

        added = [v for name, v in new_map.items() if name not in old_map]
        removed = [v for name, v in old_map.items() if name not in new_map]
        changed = []

        for name in set(old_map.keys()) & set(new_map.keys()):
            if old_map[name] != new_map[name]:
                changed.append(new_map[name])

        return {"added": added, "removed": removed, "changed": changed}

    @staticmethod
    def compare_vrf_config_with_details(
        old: list[VRFMapL3VNIList], new: list[VRFMapL3VNIList]
    ) -> dict:
        """比较VRF配置差异，包含字段级变化"""
        old_map = {v["VRFName"]: v for v in old}
        new_map = {v["VRFName"]: v for v in new}

        added = [v for name, v in new_map.items() if name not in old_map]
        removed = [v for name, v in old_map.items() if name not in new_map]
        changed = []

        for name in set(old_map.keys()) & set(new_map.keys()):
            old_vrf = old_map[name]
            new_vrf = new_map[name]
            
            # 检查是否有任何字段变化
            if old_vrf != new_vrf:
                # 标记哪些字段发生了变化
                changed_fields = {
                    k: (old_vrf.get(k), new_vrf.get(k))
                    for k in set(old_vrf.keys()) | set(new_vrf.keys())
                    if old_vrf.get(k) != new_vrf.get(k)
                }
                changed.append(
                    {
                        "name": name,
                        "old": old_vrf,
                        "new": new_vrf,
                        "changed_fields": changed_fields,
                    }
                )

        return {"added": added, "removed": removed, "changed": changed}