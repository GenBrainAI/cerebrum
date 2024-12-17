import streamlit as st
from pathlib import Path

def get_logo_path() -> str:
    """Get the path to the logo file."""
    # Try different potential locations for the logo
    potential_paths = [
        Path(__file__).parent.parent.parent.parent / "logo.png",  # From components up to src
        Path(__file__).parent.parent.parent.parent.parent / "logo.png",  # Up to project root
        Path.cwd() / "logo.png"  # Current working directory
    ]
    
    for path in potential_paths:
        if path.exists():
            return str(path)
    
    return None

def render_header(title: str, description: str = ""):
    """Render a consistent header with logo and title."""
    # Create columns for logo and title
    col1, col2 = st.columns([1, 4])
    
    with col1:
        logo_path = get_logo_path()
        if logo_path:
            st.image(logo_path, width=100)
    
    with col2:
        st.title(title)
        if description:
            st.markdown(description)
    
    st.markdown("---") 