import argparse, json, os, sys, subprocess, ipaddress, re
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
from dataclasses import dataclass, asdict


NETPLAN_DIR = Path("/etc/netplan")
HOSTNAME_FILE = Path("/etc/hostname")
HOSTS_FILE = Path("/etc/hosts")

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


if __name__ == "__main__":

    with open(NETPLAN_DIR / WRITE_NETCFG_FILE, "w") as f:
        yaml.safe_dump(netplan_config, f, sort_keys=False)
        
    #subprocess.run(["hostnamectl", "set-hostname", config_jdata["hostname"]], check=True)
    
    print(config_jdata)