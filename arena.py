from memory import Memory
from block import Block

class Arena(Memory):

    def __init__(self, max_memory:int = 65_536):
        self.max_memory = max_memory
        self.memory_size = 0
        self.blocks = {}
        self.blocks_amount = len(self.blocks)

    def add_block(self, block:Block):
        if self.memory_size + block.memory <= self.max_memory:
            self.blocks[block] = block
            self.memory_size += block.memory
        else:
            raise MemoryError("Not enough memory to add the block.")

    def remove_block(self, block:Block):
        if block in self.blocks:
            self.memory_size -= block.memory
            del self.blocks[block]
        else:
            raise MemoryError("Block not found.")