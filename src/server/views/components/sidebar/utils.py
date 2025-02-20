"""Utility functions for sidebar components."""

def truncate_tree_node_names(node):
    """Smart truncation for tree node names.
    
    Handles patterns like:
    - class_name.function_name -> [c.n]function_name
    - very.long.path.name -> [v.l.p]name
    - long_name_without_dots -> ...last_35_chars
    
    Args:
        node: TreeNode object with name and children attributes
    """
    if len(node.name) > 35:
        # Split by dot to separate class/path parts
        parts = node.name.split('.')
        if len(parts) > 1:
            # Get initials of all parts except the last
            prefix_parts = parts[:-1]
            # Get initials, filtering out empty parts
            prefix_abbrev = '.'.join(
                '.'.join(p[0] for p in part.split('_') if p)  # Filter out empty strings
                for part in prefix_parts
            )
            # Get the last part
            last_part = parts[-1]
            if len(last_part) > 25:  # Leave space for the abbreviation
                last_part = "..." + last_part[-25:]
            node.name = f"[{prefix_abbrev}]{last_part}" if prefix_abbrev else last_part
        else:
            # If no dots, just truncate
            node.name = "..." + node.name[-35:]
    
    # Recursively process children
    for child in node.children:
        truncate_tree_node_names(child) 