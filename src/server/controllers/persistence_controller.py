from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum
import boto3
import json
from ..persistence.persistence_model_factory import PersistenceModelFactory
from ..models.persistence_models import StorageLocation, StorageType


def save_to_storage(location: StorageLocation) -> str:
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    json_str = persistence_model.to_json()

    if location.type == StorageType.s3:
        try:
            response = s3_client.put_object(
                Bucket=location.location,
                Key=location.state_name,
                Body=json_str
            )
            return f"Saved to S3 at {location.location}/{location.state_name}"
        except ClientError as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif location.type == StorageType.file:
        try:
            filename = f'{location.location}/{location.state_name}'
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_str)
            return f"Saved to local file: {filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Storage type not implemented")

def load_from_storage(location: StorageLocation) -> str:
    persistence_model = PersistenceModelFactory.persistence_model("inmemory")
    if location.type == StorageType.s3:
        try:
            response = s3_client.get_object(
                Bucket=location.location,
                Key=location.state_name
            )
            state_data = response['Body'].read().decode('utf-8')
            persistence_model.from_json(json_str=state_data)
            return state_data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(status_code=404, detail="State not found")
            raise HTTPException(status_code=500, detail=str(e))
    elif location.type == StorageType.file:
        try:
            filename = f'{location.location}/{location.state_name}'
            with open(filename, 'r', encoding='utf-8') as f:
                json_str = f.read()
                persistence_model.from_json(json_str=json_str)
                return json_str
        except (IOError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            print(e)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=501, detail="Storage type not implemented")
