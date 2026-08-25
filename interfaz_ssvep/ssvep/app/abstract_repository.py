from abc import ABC, abstractmethod

class AbstractRepository(ABC):
    @abstractmethod
    def save(self, entity):
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list:
        raise NotImplementedError
    
    @abstractmethod
    def update(self, updated_entity):
        raise NotImplementedError   
    
    @abstractmethod
    def get_by_filter(self, filter_key, value):
        raise NotImplementedError
    
    @abstractmethod
    def delete(self, entity_id):
        raise NotImplementedError