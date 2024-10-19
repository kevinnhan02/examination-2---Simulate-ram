import uuid
import pandas as pd
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
            "arenas": pd.DataFrame(columns=["arena_obj", "arena_name", "arena_mem", "arena_max", "pools"])
        }
        self.object_index = {}

    def generate_unique_id(self) -> str:
        return str(uuid.uuid4())

    def add_arena(self, arena: Arena) -> None:
        arena_count = len(self.memory["arenas"]) + 1
        arena_name = f"Arena {arena_count}"
        new_arena = {
            "arena_obj": arena,
            "arena_name": arena_name,
            "arena_mem": arena.mem,
            "arena_max": arena.max_mem,
            "pools": pd.DataFrame(columns=["pool_obj", "pool_name", "pool_mem", "pool_max", "blocks"])
        }
        self.memory["arenas"] = pd.concat([self.memory["arenas"], pd.DataFrame([new_arena])], ignore_index=True)

    def add_pool(self, arena_name: str, pool: Pool) -> None:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if not arena_index.empty:
            arena_index = arena_index[0]
            pool_count = len(self.memory["arenas"].loc[arena_index, "pools"]) + 1
            new_pool = {
                "pool_obj": pool,
                "pool_name": f"pool {pool_count}",
                "pool_mem": pool.mem,
                "pool_max": pool.max_mem,
                "blocks": pd.DataFrame(columns=["block_mem", "block_max"])
            }
            self.memory["arenas"].at[arena_index, "pools"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"], pd.DataFrame([new_pool])], ignore_index=True)
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def add_block(self, arena_name: str, pool_name: str, block: Block) -> None:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if not arena_index.empty:
            arena_index = arena_index[0]
            pool_index = self.memory["arenas"].at[arena_index, "pools"][self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name].index
            if not pool_index.empty:
                pool_index = pool_index[0]
                block_count = len(self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"]) + 1
                new_block = {
                    "block_mem": block.mem,
                    "block_max": block.max_mem
                }
                self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"], pd.DataFrame([new_block])], ignore_index=True)
            else:
                raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def check_memory_exceeds(self) -> bool:
        self.total_block_memory = self.memory["arenas"]["pools"].apply(lambda pools: pools["blocks"]["block_mem"].sum()).sum()
        return self.total_block_memory

    def calculate_arena_memory(self, arena_name: str) -> int:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if arena_index.empty:
            raise ValueError(f"Arena {arena_name} does not exist.")
        arena_index = arena_index[0]
        return self.memory["arenas"].at[arena_index, "pools"]["pool_mem"].sum()

    def calculate_pool_memory(self, arena_name: str, pool_name: str) -> int:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if arena_index.empty:
            raise ValueError(f"Arena {arena_name} does not exist.")
        arena_index = arena_index[0]
        pool_index = self.memory["arenas"].at[arena_index, "pools"][self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name].index
        if pool_index.empty:
            raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        pool_index = pool_index[0]
        return self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"]["block_mem"].sum()

    def check_enough_arenas(self, obj_mem):
        required_arenas = (obj_mem // self.ram.max_arena_size) + 1
        remaining_memory = self.ram.memory - self.memory["used_ram_mem"]
        if remaining_memory < obj_mem:
            raise MemoryError("Not enough memory available to create more arenas.")
        return required_arenas

    def check_enough_pools(self, arena, obj_mem):
        required_pools = (obj_mem // self.ram.max_pool_size) + 1
        remaining_memory = arena["arena_max"] - arena["arena_mem"]
        if remaining_memory < obj_mem:
            raise MemoryError("Not enough memory available in the arena to create more pools.")
        return required_pools

    def check_enough_blocks(self, pool, obj_mem):
        required_blocks = (obj_mem // self.ram.max_block_size) + 1
        remaining_memory = pool["pool_max"] - pool["pool_mem"]
        if remaining_memory < obj_mem:
            raise MemoryError("Not enough memory available in the pool to create more blocks.")
        return required_blocks

    def fill_ram(self, obj_mem):
        remaining_memory = obj_mem
        while remaining_memory > 0:
            if self.memory["arenas"].empty or self.memory["arenas"].iloc[-1]["arena_mem"] >= self.memory["arenas"].iloc[-1]["arena_max"]:
                new_arena = Arena(0)
                self.add_arena(new_arena)
            last_arena = self.memory["arenas"].iloc[-1]
            if last_arena["arena_mem"] < last_arena["arena_max"]:
                self.fill_pools(last_arena, remaining_memory)
                remaining_memory -= min(remaining_memory, last_arena["arena_max"] - last_arena["arena_mem"])
            else:
                raise MemoryError("Not enough memory available in the arenas to allocate the object.")

    def fill_arenas(self, obj_mem):
        remaining_memory = obj_mem
        arenas = self.memory["arenas"]
        available_memory = arenas["arena_max"] - arenas["arena_mem"]
        arenas["arena_mem"] += available_memory.clip(upper=remaining_memory)
        remaining_memory -= available_memory.sum()
        if remaining_memory > 0:
            raise MemoryError("Not enough memory available in the arenas to allocate the object.")

    def fill_pools(self, arena, obj_mem):
        remaining_memory = obj_mem
        pools = arena["pools"]
        available_memory = pools["pool_max"] - pools["pool_mem"]
        pools["pool_mem"] += available_memory.clip(upper=remaining_memory)
        remaining_memory -= available_memory.sum()
        if remaining_memory > 0:
            raise MemoryError("Not enough memory available in the pools to allocate the object.")

    def fill_blocks(self, pool, obj_mem):
        remaining_memory = obj_mem
        blocks = pool["blocks"]
        available_memory = blocks["block_max"] - blocks["block_mem"]
        blocks["block_mem"] += available_memory.clip(upper=remaining_memory)
        remaining_memory -= available_memory.sum()
        if remaining_memory > 0:
            raise MemoryError("Not enough memory available in the blocks to allocate the object.")

    # def add_object(self, obj) -> str:
    #     obj_size = obj.__sizeof__()  # Calculate the size of the object
    #     obj_id = self.generate_unique_id()  # Generate a unique ID for the object
    #     self.check_memory_exceeds()  # Check if the total memory used by all blocks exceeds the available RAM

    #     if obj_size + self.total_block_memory > self.ram.memory:
    #         raise MemoryError("Object size exceeds available RAM.")  # Raise an error if memory exceeds

    #     # Calculate the required number of arenas, pools, and blocks
    #     required_arenas = (obj_size // self.ram.max_arena_size) + 1

    #     if not self.memory["arenas"].empty:
    #         last_arena = self.memory["arenas"].iloc[-1]
    #         if last_arena["arena_max"] - last_arena["arena_mem"] >= obj_size and self.check_enough_pools(last_arena, obj_size):
    #             last_arena["arena_mem"] += obj_size
    #             self.memory["used_ram_mem"] += obj_size
    #             self.fill_pools(last_arena, obj_size)
    #             self.object_index[obj_id] = {"object": obj, "size": obj_size, "paths": last_arena["pools"]["blocks"]}
    #             return obj_id

    #     while required_arenas > 0:
    #         remaining_memory = self.ram.memory - self.total_block_memory
    #         if remaining_memory > 0:
    #             new_arena = Arena(0)
    #             self.add_arena(new_arena)
    #             required_arenas -= 1
    #         else:
    #             raise MemoryError("Not enough memory available to create more arenas.")

    #     # After creating the necessary arenas, check and create the required pools and blocks
    #     for arena in self.memory["arenas"].itertuples():
    #         if self.check_enough_pools(arena, obj_size):
    #             for pool in arena.pools.itertuples():
    #                 if self.check_enough_blocks(arena, pool, obj_size):
    #                     arena.arena_mem += obj_size
    #                     self.memory["used_ram_mem"] += obj_size
    #                     self.fill_pools(arena, obj_size)
    #                     self.fill_blocks(pool, obj_size)

    #     return obj_id

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


# def main():
    # Step 1: Create a RAM instance with default memory
    # ram = RAM()

    # Step 2: Initialize the memory manager with the RAM instance
    # mem_manager = MemManager(ram)

    # Step 3: Add one arena, one pool, and one block
    # arena = Arena(0)
    # mem_manager.add_arena(arena)

    # pool = Pool(0)
    # mem_manager.add_pool("Arena 1", pool)

    # block = Block(0)
    # mem_manager.add_block("Arena 1", "pool 1", block)

    # mem_manager.memory["arenas"]

    # Step 4: Create a sample object and add it to the memory manager
    # sample_object = "test_object" * 2000
    # obj_id = mem_manager.add_object(sample_object)
    # print(f"Object ID: {obj_id}")

    # Step 5: Retrieve and print the object using its unique ID
    # retrieved_object = mem_manager.get_object(obj_id)
    # print(f"Retrieved Object: {retrieved_object}")

    # Step 6: Print the memory manager's state
    # with open("memory_manager_state.txt", "w") as file:
    #     file.write(str(mem_manager))
