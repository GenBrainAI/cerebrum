from .persistence_model import PersistenceModelBase
from .in_memory_persistence import InMemoryPersistenceModel


class PersistenceModelFactory:
    _instance: PersistenceModelBase = None

    @staticmethod
    def persistence_model(type: str = "inmemory") -> PersistenceModelBase:
        if PersistenceModelFactory._instance is None:
            if type == "inmemory":
                PersistenceModelFactory._instance = InMemoryPersistenceModel()
            else:
                raise NotImplementedError(f"Unknown persistence model type: {type}")
        return PersistenceModelFactory._instance
