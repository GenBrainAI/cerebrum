"""
Persistence model dependencies for FastAPI.
"""

from typing import Annotated
from fastapi import Depends

from .persistence_model_factory import PersistenceModelFactory
from .persistence_model import PersistenceModelBase


async def get_persistence_model() -> PersistenceModelBase:
    """
    Get the persistence model as a FastAPI dependency.
    
    Returns:
        The persistence model instance.
    """
    return PersistenceModelFactory.persistence_model()


# For type annotations in route function parameters
PersistenceModel = Annotated[PersistenceModelBase, Depends(get_persistence_model)] 