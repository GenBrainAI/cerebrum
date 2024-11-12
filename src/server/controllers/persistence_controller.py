from fastapi import FastAPI, HTTPException, Depends
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
import boto3
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.persistence_models import StorageLocation, StorageType

# Add near the top of the file, after the imports
s3_client = boto3.client('s3')

def save_to_storage(location: StorageLocation) -> str:
    try:
        # Create and serialize persistence model
        persistence_model = PersistenceModelFactory.persistence_model("inmemory")
        json_str = persistence_model.to_json()

        # Handle different storage types
        if location.type == StorageType.s3:
            response = s3_client.put_object(
                Bucket=location.location,
                Key=location.state_name,
                Body=json_str
            )
            return f"Saved to S3 at {location.location}/{location.state_name}"
            
        elif location.type == StorageType.file:
            filename = f'{location.location}/{location.state_name}'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            return f"Saved to local file: {filename}"
            
        else:
            raise HTTPException(status_code=501, detail="Storage type not implemented")

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            raise HTTPException(status_code=404, detail=f"S3 bucket '{location.location}' not found")
        elif error_code == 'AccessDenied':
            raise HTTPException(status_code=403, detail="Access denied to S3 bucket")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model configuration: {str(e)}")
        
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied writing to {filename}")
        
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"IO error writing to file: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

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
        if error_code == 'NoSuchKey':
            raise HTTPException(status_code=404, detail="State not found")
        elif error_code == 'NoSuchBucket':
            raise HTTPException(status_code=404, detail=f"S3 bucket '{location.location}' not found")
        elif error_code == 'AccessDenied':
            raise HTTPException(status_code=403, detail="Access denied to S3 bucket")
        raise HTTPException(status_code=500, detail=f"S3 error: {str(e)}")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid model configuration: {str(e)}")
        
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
        
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"IO error reading file: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
