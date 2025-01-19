"""Internal credentials tools."""
import os
import logging
import dotenv
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from .tools_metrics import ToolExecutionMetrics

logger = logging.getLogger(__name__)

class InternalCredentialsTools:
    """Tool for managing project credentials."""
    
    def __init__(self, env_path: str = None):
        """Initialize credentials tools.
        
        Args:
            env_path: Path to the .env file
        """
        project_root = str(Path(__file__).parents[2])
        self.env_path = env_path or os.path.join(project_root, '.env')
        self._execution_metrics = ToolExecutionMetrics()

    async def load_credentials(self) -> Dict[str, Any]:
        """Load credentials from .env file.
        
        Returns:
            Dictionary containing credentials
            
        Raises:
            FileNotFoundError: If the .env file does not exist
            IOError: If there is an error reading the file
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"env_path": self.env_path}
        
        try:
            logger.info(f"Loading credentials from: {self.env_path}")
            if not os.path.exists(self.env_path):
                raise FileNotFoundError(f".env file not found at {self.env_path}")
                
            creds = dotenv.dotenv_values(self.env_path)
            logger.info("Successfully loaded credentials")
            
            self._execution_metrics.success = True
            self._execution_metrics.output = "Credentials loaded successfully"
            return {"credentials": creds}
            
        except FileNotFoundError as e:
            logger.error(f"Credentials file not found: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now()

    async def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate that required credentials are present.
        
        Args:
            credentials: Dictionary of credentials to validate
            
        Returns:
            Dictionary containing validation status
            
        Raises:
            ValueError: If required credentials are missing
        """
        self._execution_metrics.start_time = datetime.now()
        self._execution_metrics.input_params = {"credentials": credentials}
        
        try:
            logger.info("Validating credentials")
            required_keys = ['API_KEY', 'DATABASE_URL']
            missing = [key for key in required_keys if key not in credentials]
            
            if missing:
                raise ValueError(f"Missing required credentials: {', '.join(missing)}")
                
            logger.info("All required credentials present")
            self._execution_metrics.success = True
            self._execution_metrics.output = "All required credentials present"
            return {"message": "All required credentials present"}
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error validating credentials: {str(e)}")
            self._execution_metrics.success = False
            self._execution_metrics.error = str(e)
            raise
            
        finally:
            self._execution_metrics.end_time = datetime.now() 