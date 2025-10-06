import argparse, json, os, sys, subprocess, ipaddress, re
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from dataclasses import dataclass, asdict


NETPLAN_DIR = Path("/etc/netplan")
HOSTNAME_FILE = Path("/etc/hostname")
HOSTS_FILE = Path("/etc/hosts")
INTERFACES = Path("/etc/network/interfaces")

JSON_CONFIG_FILE = "config.json"
WRITE_NETCFG_FILE = "01-netcfg.yaml"



def require_root():
    if os.geteuid() != 0:
        print("rootで実行してください（sudo）。", file=sys.stderr)
        sys.exit(1)



def load_json_config(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("オブジェクト読み込み失敗")
        return data
    except Exception as e:
        print(f"[ERROR] JSONの読み込みに失敗: {e}", file=sys.stderr)
        sys.exit(2)
    

config_jdata = load_json_config(JSON_CONFIG_FILE)

netplan_config = {
    "network": {
        "version": 2,
        "renderer": "networkd",
        "ethernets": {
            config_jdata["interface"]: {
                "dhcp4": False,
                "accept-ra": False,
                "addresses": [config_jdata["address"]],
                "nameservers": {
                    "addresses": config_jdata["dns"],
                },
                "routes": [
                    {"to": "default", "via":  config_jdata["gateway"], "on-link": True}
                    ]   
            }
        }
    }
}

ifupdown_config = {
    "auto": ["lo", "vmbr0"],
    "interfaces": {
        "lo": {
            "method": "loopback"
        },
        "eno1": {
            "method": "manual"
        },
        "vmbr0": {
            "method": "static",
            "address": config_jdata["address"],
            "gateway": config_jdata["gateway"],
            "bridge-ports": ["eno1"],
            "bridge-stp": "off",
            "bridge-fd": 0
        }
    },
    "include": "/etc/network/interfaces.d/*"
}

def generate_ifupdown_text(cfg: dict) -> str:
    lines = []
    for iface in cfg.get("auto", []):
        lines.append(f"auto {iface}")
    lines.append("")  

    for name, params in cfg["interfaces"].items():
        method = params.get("method", "manual")
        lines.append(f"iface {name} inet {method}")
        for key, val in params.items():
            if key == "method":
                continue
            if isinstance(val, list):
                val = " ".join(str(v) for v in val)
            lines.append(f"    {key} {val}")
        lines.append("")  
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        with open(NETPLAN_DIR / WRITE_NETCFG_FILE, "w") as f:
            yaml.safe_dump(netplan_config, f, sort_keys=False)
    except FileNotFoundError:
        print(f"[WARN] {NETPLAN_DIR} が存在しません。別の設定方式（ifupdownなど）に切り替えます。")
        with open(INTERFACES, "w") as f:
            f.write(generate_ifupdown_text(ifupdown_config))
    

    subprocess.run(["hostnamectl", "set-hostname", config_jdata["hostname"]], check=True)
    
    print(config_jdata)