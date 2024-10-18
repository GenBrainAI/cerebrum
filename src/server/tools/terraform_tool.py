import re
import json
from typing import Dict, List, Any

class TerraformTool:
    def __init__(self):
        self.terraform_config = {}

    def parse_terraform_script(self, script_content: str) -> Dict[str, Any]:
        """Parse a Terraform script and return its content as a dictionary."""
        try:
            # Simple parser for kubernetes_network_policy resource
            pattern = r'resource\s+"kubernetes_network_policy"\s+"([^"]+)"\s+{([^}]+)}'
            matches = re.findall(pattern, script_content, re.DOTALL)
            
            for resource_name, resource_content in matches:
                policy = self._parse_block(resource_content)
                self.terraform_config[resource_name] = policy
            
            return self.terraform_config
        except Exception as e:
            raise ValueError(f"Error parsing Terraform script: {str(e)}")

    def _parse_block(self, block_content: str) -> Dict[str, Any]:
        """Parse a block of Terraform configuration."""
        result = {}
        lines = block_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if '=' in line:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip().strip('"')
            elif '{' in line:
                key = line.split('{')[0].strip()
                sub_block_end = self._find_matching_brace(lines, lines.index(line))
                sub_block = '\n'.join(lines[lines.index(line)+1:sub_block_end])
                result[key] = self._parse_block(sub_block)
        return result

    def _find_matching_brace(self, lines: List[str], start_index: int) -> int:
        """Find the index of the matching closing brace."""
        brace_count = 0
        for i, line in enumerate(lines[start_index:], start=start_index):
            brace_count += line.count('{') - line.count('}')
            if brace_count == 0:
                return i
        raise ValueError("No matching brace found")

    def modify_network_policy(self, microservice_name: str, ingress_rules: List[Dict[str, Any]], egress_rules: List[Dict[str, Any]]) -> None:
        """Modify the network policy for a specific microservice."""
        policy = self.terraform_config.get(microservice_name, {})
        if not policy:
            policy = {
                "metadata": {
                    "name": f"network-policy-{microservice_name}",
                    "namespace": microservice_name
                },
                "spec": {
                    "pod_selector": {},
                    "policy_types": ["Ingress", "Egress"]
                }
            }
        
        policy["spec"]["ingress"] = ingress_rules
        policy["spec"]["egress"] = egress_rules
        
        self.terraform_config[microservice_name] = policy

    def apply_best_practices(self) -> None:
        """Apply best practices for Kubernetes network security."""
        for policy in self.terraform_config.values():
            spec = policy.get("spec", {})
            if "ingress" in spec and spec["ingress"]:
                if "policy_types" not in spec:
                    spec["policy_types"] = []
                if "Ingress" not in spec["policy_types"]:
                    spec["policy_types"].append("Ingress")
            if "egress" in spec and spec["egress"]:
                if "policy_types" not in spec:
                    spec["policy_types"] = []
                if "Egress" not in spec["policy_types"]:
                    spec["policy_types"].append("Egress")

    def generate_terraform_script(self) -> str:
        """Generate a Terraform script from the current configuration."""
        script = ""
        for resource_name, policy in self.terraform_config.items():
            script += f'resource "kubernetes_network_policy" "{resource_name}" {{\n'
            script += self._dict_to_hcl(policy, 1)
            script += "}\n\n"
        return script

    def _dict_to_hcl(self, d: Dict[str, Any], indent: int = 0) -> str:
        """Convert a dictionary to HCL format."""
        result = ""
        for key, value in d.items():
            if isinstance(value, dict):
                result += f"{' ' * indent}{key} {{\n"
                result += self._dict_to_hcl(value, indent + 2)
                result += f"{' ' * indent}}}\n"
            elif isinstance(value, list):
                result += f"{' ' * indent}{key} = [\n"
                for item in value:
                    if isinstance(item, dict):
                        result += f"{' ' * (indent + 2)}{{\n"
                        result += self._dict_to_hcl(item, indent + 4)
                        result += f"{' ' * (indent + 2)}}},\n"
                    else:
                        result += f"{' ' * (indent + 2)}\"{item}\",\n"
                result += f"{' ' * indent}]\n"
            else:
                result += f"{' ' * indent}{key} = \"{value}\"\n"
        return result

    def validate_changes(self) -> List[str]:
        """Validate the changes made to the Terraform configuration."""
        warnings = []
        if not self.terraform_config:
            warnings.append("No network policies defined in the Terraform configuration.")
        for resource_name, policy in self.terraform_config.items():
            if "spec" not in policy:
                warnings.append(f"Missing 'spec' in network policy for {resource_name}")
            elif "ingress" not in policy["spec"] and "egress" not in policy["spec"]:
                warnings.append(f"Neither ingress nor egress rules defined for {resource_name}")
        return warnings

# Example usage:
# tf_tool = TerraformTool()
# tf_tool.parse_terraform_script(existing_script)
# tf_tool.modify_network_policy("microservice-x", 
#     ingress_rules=[{"from": [{"pod_selector": {"match_labels": {"app": "allowed-ingress-service"}}}]}],
#     egress_rules=[{"to": [{"pod_selector": {"match_labels": {"app": "allowed-egress-service"}}}]}]
# )
# tf_tool.apply_best_practices()
# new_script = tf_tool.generate_terraform_script()
# warnings = tf_tool.validate_changes()