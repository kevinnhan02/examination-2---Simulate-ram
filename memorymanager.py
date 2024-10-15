from blocktest_2 import Block
from arenatest_2 import Arena
from pooltest_2 import Pool
from ram import RAM

class MemManager:
    def __init__(self, ram:RAM) -> None:
        """
        Initialize the memory manager with RAM.

        :param ram: An instance of RAM.
        """
        self.ram = ram
        self.memory = {
            "ram_mem": ram.memory,
            "used_ram_mem": 0,
            "arenas": {}}

    def add_arena(self, arena: Arena) -> None:
        """
        Add an arena to the memory manager.

        :param arena: An instance of Arena.
        """
        arena_count = len(self.memory["arenas"]) + 1
        self.memory["arenas"][f"Arena{arena_count}"] = {"arena_obj": arena, \
                                                        "arena_mem": arena.mem,
                                                        "arena_max": arena.max_mem, \
                                                        "pools": {}}

    def add_pool(self, arena_name: str, pool: Pool) -> None:
        """
        Add a pool to a specific arena in the memory manager.

        :param arena_name: The name of the arena to add the pool to.
        :param pool: An instance of Pool.
        """
        if arena_name in self.memory["arenas"]:
            pool_count = len(self.memory["arenas"][arena_name]["pools"]) + 1
            self.memory["arenas"][arena_name]["pools"][f"pool{pool_count}"] = {"pool_obj": pool,\
                                                                               "pool_mem": pool.mem, \
                                                                               "pool_max": pool.max_mem, \
                                                                               "blocks": {}}
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def add_block(self, arena_name: str, pool_name: str, block: Block) -> None:
        """
        Add a block to a specific pool in a specific arena in the memory manager.

        :param arena_name: The name of the arena containing the pool.
        :param pool_name: The name of the pool to add the block to.
        :param block: An instance of Block.
        """
        if arena_name in self.memory["arenas"]:
            if pool_name in self.memory["arenas"][arena_name]["pools"]:
                block_count = len(self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"]) + 1
                self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"][f"block{block_count}"] = {"block_mem":block.mem,\
                                                                                                          "block_max": block.max_mem}
            else:
                raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def __repr__(self) -> str:
        """
        Return a string representation of the memory manager.
        """
        return f"Memory Manager: {self.memory}"
