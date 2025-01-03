"""Internal credentials tools."""
import os
import logging
import dotenv
from typing import Dict, Any
from pathlib import Path

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

    async def load_credentials(self) -> Dict[str, Any]:
        """Load credentials from .env file.
        
        Returns:
            Dictionary containing credentials or error message
        """
        try:
            logger.info(f"Loading credentials from: {self.env_path}")
            creds = dotenv.dotenv_values(self.env_path)
            logger.info("Successfully loaded credentials")
            return {"status": "success", "credentials": creds}
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def validate_credentials(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Validate that required credentials are present.
        
        Args:
            credentials: Dictionary of credentials to validate
            
        Returns:
            Dictionary containing validation status
        """
        try:
            logger.info("Validating credentials")
            required_keys = ['API_KEY', 'DATABASE_URL']
            missing = [key for key in required_keys if key not in credentials]
            
            if missing:
                logger.warning(f"Missing required credentials: {missing}")
                return {
                    "status": "error",
                    "message": f"Missing required credentials: {', '.join(missing)}"
                }
                
            logger.info("All required credentials present")
            return {"status": "success", "message": "All required credentials present"}
        except Exception as e:
            logger.error(f"Error validating credentials: {str(e)}")
            return {"status": "error", "message": str(e)} 