from fastapi import FastAPI, HTTPException, Depends
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from enum import Enum
import boto3
import json
import logging
import traceback
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.persistence_models import StorageLocation, StorageType
from pathlib import Path

# Add near the top of the file, after the imports
s3_client = boto3.client('s3')

def save_to_storage(location: StorageLocation, context_state: Optional[Dict] = None) -> str:
    """Save current state to storage."""
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    
    # Get the state as JSON
    json_str = persistence_model.to_json()
    
    # If we have context state, add it to the JSON
    if context_state:
        # Parse existing JSON
        state_data = json.loads(json_str)
        # Add context state
        state_data['context_state'] = context_state
        # Convert back to JSON
        json_str = json.dumps(state_data, indent=4)
    
    # Save based on storage type
    if location.type == StorageType.file:
        # Remove .json extension if it exists and add it back once
        base_name = location.state_name.replace('.json', '')
        file_path = Path(location.location) / f"{base_name}.json"
        with open(file_path, "w") as f:
            f.write(json_str)
        return f"State saved to {file_path}"
    else:
        raise ValueError(f"Unsupported storage type: {location.type}")

def load_from_storage(location: StorageLocation) -> str:
    try:
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        
        if location.type == StorageType.s3:
            response = s3_client.get_object(
                Bucket=location.location,
                Key=location.state_name
            )
            state_data = response['Body'].read().decode('utf-8')
            persistence_model.from_json(json_str=state_data)
            return state_data
            
        elif location.type == StorageType.file:
            filename = f'{location.location}/{location.state_name}'
            with open(filename, 'r', encoding='utf-8') as f:
                json_str = f.read()
                persistence_model.from_json(json_str=json_str)
                return json_str
                
        else:
            raise HTTPException(status_code=501, detail="Storage type not implemented")
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logging.error(f"AWS Client Error:\n{traceback.format_exc()}")
        if error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="State not found")
        elif error_code == 'NoSuchBucket':
            raise HTTPException(status_code=404, detail=f"S3 bucket '{location.location}' not found")
        elif error_code == 'AccessDenied':
            raise HTTPException(status_code=403, detail="Access denied to S3 bucket")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
        
    except ValueError as e:
        logging.error(f"ValueError:\n{traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid model configuration: {str(e)}")
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        
    except IOError as e:
        logging.error(f"IOError:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"IO error reading file: {str(e)}")
        
    except Exception as e:
        logging.error(f"Unexpected error:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
