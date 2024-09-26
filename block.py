from memory import Memory
import uuid

class Block(Memory):
    def __init__(self, max_memory):
        self.max_memory = max_memory
        self.memory = 0
        self.unit_data = {}

    def write(self, value):
        if value in self.unit_data.values():
            return [key for key, val in self.unit_data.items() if val == value][0]

        value_size = value.__sizeof__()
        if self.memory + value_size <= self.max_memory:
            unique_address = uuid.uuid4().int
            self.unit_data[unique_address] = value
            self.memory += value_size
        else:
            raise MemoryError("Not enough memory to write the value.")

    def read(self, address):
        return self.unit_data[address]

    def get_value_id(self, value):
        return self.get_key_by_value(value, self.unit_data)

