import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import os
import json
import nbformat
import base64
import io
import tempfile
import subprocess
from typing import Optional, Dict, Any, List, Union

class NotebookViewerComponent:
    """Component for displaying Jupyter notebooks in Streamlit."""
    
    def __init__(self):
        """Initialize the component."""
        # Check if streamlit_jupyter is available
        self.has_streamlit_jupyter = False
        try:
            import streamlit_jupyter
            self.has_streamlit_jupyter = True
        except ImportError:
            pass
    
    def render(self, notebook_path: str):
        """Render a Jupyter notebook in Streamlit."""
        # Check if the notebook exists
        if not Path(notebook_path).exists():
            st.error(f"Notebook not found: {notebook_path}")
            return
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Native Viewer", "Interactive Notebook", "Code View"])
        
        # Load the notebook using nbformat
        try:
            with open(notebook_path, 'r', encoding='utf-8') as f:
                notebook_content = f.read()
                notebook = nbformat.reads(notebook_content, as_version=4)
        except Exception as e:
            st.error(f"Error loading notebook: {str(e)}")
            return
        
        # Tab 1: Native Viewer - Display cells directly in Streamlit
        with tab1:
            self._render_notebook_native(notebook)
        
        # Tab 2: Interactive Notebook - Using jupyterlite in an iframe
        with tab2:
            if self.has_streamlit_jupyter:
                try:
                    from streamlit_jupyter import StreamlitPython
                    StreamlitPython(notebook_path)
                except Exception as e:
                    st.error(f"Error using streamlit_jupyter: {str(e)}")
                    self.render_as_iframe(notebook_path)
            else:
                self.render_as_iframe(notebook_path)
        
        # Tab 3: Code View - Show the notebook source
        with tab3:
            try:
                # Format JSON for better readability
                formatted_content = json.dumps(json.loads(notebook_content), indent=2)
                st.code(formatted_content, language="json")
            except Exception:
                # If JSON formatting fails, just show the raw content
                st.code(notebook_content, language="json")
    
    def _render_notebook_native(self, notebook: nbformat.NotebookNode):
        """Render notebook cells directly in Streamlit."""
        st.write("# " + notebook.metadata.get('title', 'Notebook Viewer'))
        
        # Process cells
        for i, cell in enumerate(notebook.cells):
            cell_type = cell.get('cell_type', '')
            source = cell.get('source', '')
            
            # Add a small divider between cells
            if i > 0:
                st.markdown("---")
            
            # Create an expandable container for each cell
            with st.expander(f"Cell {i+1} ({cell_type})", expanded=True):
                # Handle different cell types
                if cell_type == 'markdown':
                    st.markdown(source)
                
                elif cell_type == 'code':
                    # Show code
                    st.code(source, language="python")
                    
                    # Show outputs if any
                    if 'outputs' in cell and cell['outputs']:
                        st.write("**Outputs:**")
                        for output in cell['outputs']:
                            self._render_output(output)
    
    def _render_output(self, output: Dict[str, Any]):
        """Render a notebook cell output."""
        output_type = output.get('output_type', '')
        
        if output_type == 'stream':
            st.text(output.get('text', ''))
        
        elif output_type in ['display_data', 'execute_result']:
            data = output.get('data', {})
            
            # Handle text/plain output
            if 'text/plain' in data:
                st.code(data['text/plain'], language="text")
            
            # Handle text/html output
            if 'text/html' in data:
                st.markdown(data['text/html'], unsafe_allow_html=True)
            
            # Handle image/png output
            if 'image/png' in data:
                try:
                    image_data = base64.b64decode(data['image/png'])
                    st.image(image_data)
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")
        
        elif output_type == 'error':
            ename = output.get('ename', 'Error')
            evalue = output.get('evalue', '')
            traceback = output.get('traceback', [])
            
            st.error(f"**{ename}**: {evalue}")
            if traceback:
                st.code('\n'.join(traceback), language="python")
    
    def render_as_iframe(self, notebook_path: str):
        """Render notebook in an iframe."""
        st.info("Using HTML viewer for notebook preview.")
        
        # Convert notebook to HTML
        html_content = self._convert_notebook_to_html(notebook_path)
        
        if html_content:
            # Display HTML in an iframe
            components.html(html_content, height=600, scrolling=True)
        else:
            st.error("Failed to render notebook as HTML.")
            # Fallback to a basic display
            try:
                with open(notebook_path, 'r', encoding='utf-8') as f:
                    st.code(f.read(), language="python")
            except Exception as e:
                st.error(f"Failed to display notebook: {str(e)}")
    
    def _convert_notebook_to_html(self, notebook_path: str) -> Optional[str]:
        """Convert a Jupyter notebook to HTML.
        
        Args:
            notebook_path: Path to the notebook file
            
        Returns:
            HTML content as string or None if conversion failed
        """
        try:
            # Create a temporary file for the HTML output
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                temp_html_path = temp_html.name
            
            # Run nbconvert to convert notebook to HTML
            process = subprocess.run(
                ['jupyter', 'nbconvert', '--to', 'html', 
                 '--output', temp_html_path, notebook_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                st.error(f"Error converting notebook to HTML: {process.stderr}")
                return None
            
            # Read the HTML content
            with open(temp_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Clean up the temporary file
            os.unlink(temp_html_path)
            
            return html_content
            
        except Exception as e:
            st.error(f"Exception during notebook conversion: {str(e)}")
            return None 