import pytest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import sys
import os
import streamlit as st
from src.server.views.components.notebook_viewer_component import NotebookViewerComponent

def test_notebook_viewer_init():
    """Test notebook viewer initialization."""
    # Test with streamlit_jupyter available
    with patch.dict('sys.modules', {'streamlit_jupyter': MagicMock()}):
        component = NotebookViewerComponent()
        assert component.has_streamlit_jupyter is True
    
    # Test without streamlit_jupyter
    with patch.dict('sys.modules', {'streamlit_jupyter': None}):
        with patch('importlib.import_module', side_effect=ImportError):
            component = NotebookViewerComponent()
            assert component.has_streamlit_jupyter is False

def test_notebook_viewer_render_file_not_found():
    """Test notebook viewer when file is not found."""
    component = NotebookViewerComponent()
    
    # Mock Path.exists to return False
    with patch.object(Path, 'exists', return_value=False), \
         patch('streamlit.error') as mock_error, \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]):
        
        component.render('nonexistent.ipynb')
        
        # Check error was displayed
        mock_error.assert_called_once()
        assert "Notebook not found" in mock_error.call_args[0][0]

def test_notebook_viewer_render_with_streamlit_jupyter():
    """Test notebook viewer rendering with streamlit_jupyter."""
    component = NotebookViewerComponent()
    component.has_streamlit_jupyter = True
    
    # Mock a successful render
    with patch.object(Path, 'exists', return_value=True), \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]), \
         patch('streamlit.code') as mock_code, \
         patch('builtins.open', mock_open(read_data='notebook content')), \
         patch('streamlit_jupyter.StreamlitPython') as mock_streamlit_python:
        
        component.render('test.ipynb')
        
        # Check if StreamlitPython was called
        mock_streamlit_python.assert_called_once_with('test.ipynb')
        mock_code.assert_called_once()

def test_notebook_viewer_render_fallback():
    """Test notebook viewer fallback rendering."""
    component = NotebookViewerComponent()
    component.has_streamlit_jupyter = False
    
    # Mock the fallback render
    with patch.object(Path, 'exists', return_value=True), \
         patch('streamlit.write') as mock_write, \
         patch('streamlit.tabs', return_value=[MagicMock(), MagicMock()]), \
         patch('streamlit.code') as mock_code, \
         patch('builtins.open', mock_open(read_data='notebook content')), \
         patch.object(component, 'render_as_iframe') as mock_render_iframe:
        
        component.render('test.ipynb')
        
        # Check if fallback was called
        mock_render_iframe.assert_called_once_with('test.ipynb')
        mock_code.assert_called_once()

def test_convert_notebook_to_html():
    """Test notebook conversion to HTML."""
    component = NotebookViewerComponent()
    
    # Mock subprocess.run for successful conversion
    with patch('tempfile.NamedTemporaryFile', return_value=MagicMock(name='test.html')), \
         patch('subprocess.run', return_value=MagicMock(returncode=0)), \
         patch('builtins.open', mock_open(read_data='<html>content</html>')), \
         patch('os.unlink'):
        
        html = component._convert_notebook_to_html('test.ipynb')
        
        # Check if HTML was returned
        assert html == '<html>content</html>'

def test_convert_notebook_to_html_error():
    """Test notebook conversion error handling."""
    component = NotebookViewerComponent()
    
    # Mock subprocess.run for failed conversion
    with patch('tempfile.NamedTemporaryFile', return_value=MagicMock(name='test.html')), \
         patch('subprocess.run', return_value=MagicMock(returncode=1, stderr='conversion error')), \
         patch('streamlit.error') as mock_error:
        
        html = component._convert_notebook_to_html('test.ipynb')
        
        # Check if error was displayed
        mock_error.assert_called_once()
        assert html is None 