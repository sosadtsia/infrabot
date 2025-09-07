"""
Ansible runner utility for executing playbooks and managing inventory
"""

import subprocess
import yaml
import tempfile
import os
from pathlib import Path
from typing import Dict, Optional, List

class AnsibleRunner:
    """Utility for running Ansible playbooks and commands"""

    def __init__(self, inventory_path: Optional[str] = None):
        self.inventory_path = inventory_path
        self.default_inventory = self._create_default_inventory()

    def _create_default_inventory(self) -> str:
        """Create a default inventory file for localhost"""
        inventory_content = """
[local]
localhost ansible_connection=local

[all:vars]
ansible_python_interpreter=/usr/bin/python3
"""

        # Create temp inventory file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(inventory_content.strip())
            return f.name

    def run_playbook(self, playbook_path: str,
                    inventory: Optional[str] = None,
                    extra_vars: Optional[Dict] = None,
                    check_mode: bool = False,
                    verbose: int = 0) -> Dict:
        """Execute an Ansible playbook"""

        # Use provided inventory or default
        inv_path = inventory or self.inventory_path or self.default_inventory

        # Build ansible-playbook command
        cmd = ["ansible-playbook", playbook_path, "-i", inv_path]

        # Add extra options
        if check_mode:
            cmd.append("--check")

        if verbose > 0:
            cmd.append(f"-{'v' * min(verbose, 4)}")

        if extra_vars:
            extra_vars_str = " ".join([f"{k}={v}" for k, v in extra_vars.items()])
            cmd.extend(["--extra-vars", extra_vars_str])

        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Playbook execution timed out",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd)
            }

    def run_ad_hoc(self, hosts: str, module: str,
                   args: Optional[str] = None,
                   inventory: Optional[str] = None,
                   become: bool = False) -> Dict:
        """Execute an Ansible ad-hoc command"""

        # Use provided inventory or default
        inv_path = inventory or self.inventory_path or self.default_inventory

        # Build ansible command
        cmd = ["ansible", hosts, "-i", inv_path, "-m", module]

        if args:
            cmd.extend(["-a", args])

        if become:
            cmd.append("--become")

        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(cmd)
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command execution timed out",
                "command": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "command": " ".join(cmd)
            }

    def validate_playbook(self, playbook_content: str) -> Dict:
        """Validate Ansible playbook syntax"""
        try:
            # Parse YAML
            playbook = yaml.safe_load(playbook_content)

            # Basic validation
            if not isinstance(playbook, list):
                return {
                    "valid": False,
                    "error": "Playbook must be a list of plays"
                }

            for play in playbook:
                if not isinstance(play, dict):
                    return {
                        "valid": False,
                        "error": "Each play must be a dictionary"
                    }

                # Check required fields
                if 'hosts' not in play:
                    return {
                        "valid": False,
                        "error": "Each play must have a 'hosts' field"
                    }

            # Create temp file and run syntax check
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(playbook_content)
                temp_path = f.name

            try:
                cmd = ["ansible-playbook", "--syntax-check", temp_path]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                return {
                    "valid": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }

            finally:
                os.unlink(temp_path)

        except yaml.YAMLError as e:
            return {
                "valid": False,
                "error": f"YAML syntax error: {e}"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }

    def list_hosts(self, inventory: Optional[str] = None) -> Dict:
        """List all hosts in inventory"""
        inv_path = inventory or self.inventory_path or self.default_inventory

        try:
            cmd = ["ansible-inventory", "-i", inv_path, "--list"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import json
                inventory_data = json.loads(result.stdout)
                return {
                    "success": True,
                    "inventory": inventory_data
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def ping_hosts(self, hosts: str = "all",
                   inventory: Optional[str] = None) -> Dict:
        """Ping hosts to test connectivity"""
        return self.run_ad_hoc(hosts, "ping", inventory=inventory)

    def get_facts(self, hosts: str = "all",
                  inventory: Optional[str] = None) -> Dict:
        """Gather facts from hosts"""
        return self.run_ad_hoc(hosts, "setup", inventory=inventory)

    def cleanup(self):
        """Clean up temporary files"""
        try:
            if hasattr(self, 'default_inventory') and os.path.exists(self.default_inventory):
                os.unlink(self.default_inventory)
        except Exception:
            pass  # Ignore cleanup errors
