import uuid
from blocktest_2 import Block
from arenatest_2 import Arena
from pooltest_2 import Pool
from ram import RAM

class MemManager:
    def __init__(self, ram: RAM) -> None:
        self.ram = ram
        self.memory = {
            "ram_mem": ram.memory,
            "used_ram_mem": 0,
            "arenas": {}
        }
        self.arena_paths = []
        self.pool_paths = []
        self.block_paths = []
        self.object_index = {}

    def generate_unique_id(self) -> str:
        return str(uuid.uuid4())

    def add_arena(self, arena: Arena) -> None:
        arena_count = len(self.memory["arenas"]) + 1
        arena_name = f"Arena {arena_count}"
        self.memory["arenas"][arena_name] = {
            "arena_obj": arena,
            "arena_name": arena_name,
            "arena_mem": arena.mem,
            "arena_max": arena.max_mem,
            "pools": {}
        }
        self.arena_paths.append(self.memory["arenas"][arena_name])

    def add_pool(self, arena_name: str, pool: Pool) -> None:
        if arena_name in self.memory["arenas"]:
            pool_count = len(self.memory["arenas"][arena_name]["pools"]) + 1
            self.memory["arenas"][arena_name]["pools"][f"pool {pool_count}"] = {
                "pool_obj": pool,
                "pool_name": f"pool {pool_count}",
                "pool_mem": pool.mem,
                "pool_max": pool.max_mem,
                "blocks": {}
            }
            self.pool_paths.append(self.memory["arenas"][arena_name]["pools"][f"pool {pool_count}"])
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def add_block(self, arena_name: str, pool_name: str, block: Block) -> None:
        if arena_name in self.memory["arenas"]:
            if pool_name in self.memory["arenas"][arena_name]["pools"]:
                block_count = len(self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"]) + 1
                self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"][f"block {block_count}"] = {
                    "block_mem": block.mem,
                    "block_max": block.max_mem
                }
                self.block_paths.append(self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"][f"block {block_count}"])
            else:
                raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def check_memory_exceeds(self) -> bool:
        self.total_block_memory = sum(
            block["block_mem"]
            for arena in self.memory["arenas"].values()
            for pool in arena["pools"].values()
            for block in pool["blocks"].values()
        )
        return self.total_block_memory

    def calculate_arena_memory(self, arena_name: str) -> int:
        if arena_name not in self.memory["arenas"]:
            raise ValueError(f"Arena {arena_name} does not exist.")
        return sum(
            block["block_mem"]
            for pool in self.memory["arenas"][arena_name]["pools"].values()
            for block in pool["blocks"].values()
        )

    def calculate_pool_memory(self, arena_name: str, pool_name: str) -> int:
        if arena_name not in self.memory["arenas"]:
            raise ValueError(f"Arena {arena_name} does not exist.")
        if pool_name not in self.memory["arenas"][arena_name]["pools"]:
            raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        return sum(
            block["block_mem"]
            for block in self.memory["arenas"][arena_name]["pools"][pool_name]["blocks"].values()
        )

    def check_enough_pools(self, arena, obj_mem):
        required_pools = (obj_mem // self.ram.max_pool_size) + 1
        while required_pools > 0:
            remaining_memory = arena["arena_max"] - arena["arena_mem"]
            if remaining_memory > 0:
                new_pool = Pool()
                self.add_pool(arena["arena_name"], new_pool)
                required_pools -= 1
            else:
                raise MemoryError("Not enough memory available in the arena to create more pools.")
        return required_pools == 0

    def check_enough_blocks(self, arena, pool, obj_mem):
        required_blocks = (obj_mem // self.ram.max_block_size) + 1
        while required_blocks > 0:
            remaining_memory = pool["pool_max"] - pool["pool_mem"]
            if remaining_memory > 0:
                new_block = Block()
                self.add_block(arena["arena_name"], pool["pool_name"], new_block)
                required_blocks -= 1
            else:
                pass
        return required_blocks == 0

    def fill_pools(self, arena, obj_mem):
        remaining_memory = obj_mem
        for pool in arena["pools"].values():
            if remaining_memory <= 0:
                break
            available_memory = pool["pool_max"] - pool["pool_mem"]
            if available_memory > 0:
                if remaining_memory <= available_memory:
                    pool["pool_mem"] += remaining_memory
                    remaining_memory = 0
                else:
                    pool["pool_mem"] += available_memory
                    remaining_memory -= available_memory
        if remaining_memory > 0:
            raise MemoryError("Not enough memory available in the pools to allocate the object.")

    def fill_blocks(self, pool, obj_mem):
        remaining_memory = obj_mem
        for block in pool["blocks"].values():
            if remaining_memory <= 0:
                break
            available_memory = block["block_max"] - block["block_mem"]
            if available_memory > 0:
                if remaining_memory <= available_memory:
                    block["block_mem"] += remaining_memory
                    remaining_memory = 0
                else:
                    block["block_mem"] += available_memory
                    remaining_memory -= available_memory
        if remaining_memory > 0:
            raise MemoryError("Not enough memory available in the blocks to allocate the object.")

    def add_object(self, obj) -> str:
        obj_size = obj.__sizeof__()  # Calculate the size of the object
        remaining_size = obj_size
        obj_id = self.generate_unique_id()  # Generate a unique ID for the object
        self.check_memory_exceeds()  # Check if the total memory used by all blocks exceeds the available RAM

        if obj_size + self.total_block_memory > self.ram.memory:
            raise MemoryError("Object size exceeds available RAM.")  # Raise an error if memory exceeds

        # Calculate the required number of arenas, pools, and blocks
        required_arenas = (obj_size // self.ram.max_arena_size) + 1

        obj_mem = obj_size

        if self.arena_paths:
            last_arena = self.arena_paths[-1]
            if last_arena["arena_max"] - last_arena["arena_mem"] >= obj_mem and self.check_enough_pools(last_arena, obj_mem):
                last_arena["arena_mem"] += obj_mem
                self.memory["used_ram_mem"] += obj_mem
                for pool in last_arena["pools"].values():
                    if self.check_enough_blocks(last_arena,pool, obj_mem):
                        self.fill_pools(last_arena, obj_mem)
                self.object_index[obj_id] = {"object": obj, "size": obj_size, "paths": self.block_paths}
                return obj_id
        else:
            for arena in self.arena_paths:
                if arena["arena_max"] - arena["arena_mem"] >= obj_mem:
                    arena["arena_mem"] += obj_mem
                if obj_mem <= 0:
                    print("Need more arenas")
                    required_arenas += 1

        while required_arenas > 0:
            remaining_memory = self.ram.memory - self.total_block_memory
            if remaining_memory > 0:
                new_arena = Arena(0)
                self.add_arena(new_arena)
                required_arenas -= 1
            else:
                print("Enough arenas")

        # After creating the necessary arenas, check and create the required pools and blocks
        for arena in self.arena_paths:
            if self.check_enough_pools(arena, remaining_size):
                for pool in arena["pools"].values():
                    if self.check_enough_blocks(arena, pool, obj_mem):
                        arena["arena_mem"] += obj_mem
                        self.memory["used_ram_mem"] += obj_mem
                        self.fill_pools(arena, remaining_size)
                        self.fill_blocks(pool, remaining_size)

        return obj_id

    def get_object(self, obj_id: str):
        """
        Retrieve an object by its unique ID.

        :param obj_id: The unique ID of the object.
        :return: The object.
        """
        if obj_id in self.object_index:
            return self.object_index[obj_id]["object"]
        else:
            raise ValueError(f"Object with ID {obj_id} does not exist.")

    def __repr__(self) -> str:
        """
        Return a string representation of the memory manager.
        """
        return f"Memory Manager: {self.memory}"


def main():
    # Step 1: Create a RAM instance with default memory
    ram = RAM()

    # Step 2: Initialize the memory manager with the RAM instance
    mem_manager = MemManager(ram)

    # Step 4: Create a sample object and add it to the memory manager
    sample_object = "test_object" * 2000
    obj_id = mem_manager.add_object(sample_object)
    print(f"Object ID: {obj_id}")

    # # Step 5: Retrieve and print the object using its unique ID
    # retrieved_object = mem_manager.get_object(obj_id)
    # print(f"Retrieved Object: {retrieved_object}")

    # Step 6: Print the memory manager's state
    with open("memory_manager_state.txt", "w") as file:
        file.write(str(mem_manager))



if __name__ == "__main__":
    main()