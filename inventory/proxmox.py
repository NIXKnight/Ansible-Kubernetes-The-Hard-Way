#!/usr/bin/env python

# This inventory script is mostly generated by ChatGPT with minor changes from me.

import json
import os
from proxmoxer import ProxmoxAPI
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single InsecureRequestWarning from urllib3
warnings.simplefilter('ignore', InsecureRequestWarning)

# Retrieve credentials from environment variables
proxmox_api_host = os.environ.get('PROXMOX_API_HOST')
proxmox_api_user = os.environ.get('PROXMOX_API_USER')
proxmox_api_password = os.environ.get('PROXMOX_API_PASSWORD')

# Check if all required environment variables are set
if not all([proxmox_api_host, proxmox_api_user, proxmox_api_password]):
    raise ValueError("Please set all required environment variables: PROXMOX_API_HOST, PROXMOX_API_USER, PROXMOX_API_PASSWORD")

# Connect to Proxmox
proxmox = ProxmoxAPI(proxmox_api_host, user=proxmox_api_user, password=proxmox_api_password, verify_ssl=False)

# Fetch VMs/containers
nodes = proxmox.nodes.get()

# Initialize inventory
inventory = {"_meta": {"hostvars": {}}}

# Process each node
for node in nodes:
    for vm in proxmox.nodes(node["node"]).qemu.get():
        vm_name = vm['name']
        vm_tags = vm['tags'].split(';') if 'tags' in vm else []

        # Attempt to get IP address from QEMU Guest Agent
        try:
            ip_info = proxmox.nodes(node["node"]).qemu(vm['vmid']).agent('network-get-interfaces').get()
            ip_addresses = [ip['ip-address'] for iface in ip_info['result'] if 'ip-addresses' in iface
                            for ip in iface['ip-addresses'] if ip['ip-address-type'] == 'ipv4' and ip['ip-address'] != '127.0.0.1']
        except Exception as e:
            ip_addresses = []
            print(f"Could not retrieve IP for VM {vm_name}: {e}")

        # Skip VM if no valid IP address is found
        if not ip_addresses:
            continue

        primary_ip = ip_addresses[0]

        # Create groups based on tags and add VM details to hostvars using IP as the key
        for tag in vm_tags:
            if tag not in inventory:
                inventory[tag] = {"hosts": []}
            inventory[tag]["hosts"].append(primary_ip)
            inventory["_meta"]["hostvars"][primary_ip] = {"proxmox_node": node["node"], "vm_id": vm["vmid"], "vm_name": vm_name}

# Output inventory in JSON format
print(json.dumps(inventory, indent=4))