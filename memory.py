from abc import ABC, abstractmethod

class Memory(ABC):
    @abstractmethod
    def read(self, address):
        pass

    @abstractmethod
    def write(self, address, value):
        pass

    def get_key_by_value(self, value, data):
        for key, val in self.unit_data.items():
            if val == value:
                return key
        return None