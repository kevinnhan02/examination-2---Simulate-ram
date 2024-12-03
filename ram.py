class RAM:
    def __init__(self, memory:int = 17_179_869_184) -> None:
        self.memory = memory
        self.max_arena_size = 256 * 1024  # 256 KB
        self.max_pool_size = 4 * 1024     # 4 KB
        self.max_block_size = 512         # 512 bytes

    def add_memory(self, amount: int) -> None:
        self.memory += amount

    def subtract_memory(self, amount: int) -> None:
        if amount > self.memory:
            raise ValueError("Cannot subtract more memory than is available")
        self.memory -= amount

    def get_remaining_unused_mem(self) -> int:
        return self.memory

    def check_enough_arenas(self, obj_mem: int) -> int:
        return (obj_mem // self.max_arena_size) + 1

    def check_enough_pools(self, obj_mem: int) -> int:
        return (obj_mem // self.max_pool_size) + 1

    def check_enough_blocks(self, obj_mem: int) -> int:
        return (obj_mem // self.max_block_size) + 1
