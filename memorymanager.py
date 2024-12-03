import uuid
import pandas as pd # type: ignore
from block import Block
from arena import Arena
from pool import Pool
from ram import RAM

class MemManager:
    def __init__(self, ram: RAM) -> None:
        self.ram = ram
        self.memory = {
            "ram_mem": ram.memory,
            "used_ram_mem": 0,
            "arenas": pd.DataFrame(columns=["arena_obj", "arena_name", "pools"])
        }
        self.object_index = {}
        self.paths = {}

    def generate_unique_id(self) -> str:
        return str(uuid.uuid4())

    def add_object(self, obj) -> str:
        obj_id = self.generate_unique_id()
        obj_size = obj.__sizeof__()

        # Use fill_ram to allocate memory for the object
        self.fill_ram(obj_size)

        # Check if there are any existing arenas
        if self.memory["arenas"].empty:
            arena_name = "Arena 1"
            new_arena = Arena(0)  # Create the first arena if none exists
            self.add_arena(new_arena)
        else:
            arena_name = self.memory["arenas"].iloc[0]["arena_name"]  # Use the first arena

        # Update the object index
        if arena_name not in self.object_index:
            self.object_index[arena_name] = {}

        self.object_index[arena_name].update({obj_id: {"object": obj}})

        print(f"Added object with ID '{obj_id}' to {arena_name}")
        return obj_id

    def get_blocks(self):
        """Generator that yields all blocks in the memory manager."""
        return (block
                for arena in self.memory["arenas"].itertuples()
                for pool in arena.pools.itertuples()
                for block in pool.blocks.itertuples())

    def remove_object(self, obj_id: str) -> None:
        """Remove an object or block from memory."""
        # Remove from object_index if present
        obj_size = next((objects[obj_id]["object"].__sizeof__() 
                        for arena_name, objects in self.object_index.items() 
                        if obj_id in objects), 0)
        
        if obj_size:
            arena_name = next(name for name, objects in self.object_index.items() if obj_id in objects)
            del self.object_index[arena_name][obj_id]
            print(f"Removed object with ID '{obj_id}' from {arena_name}")

        # Remove from paths if present
        if obj_id in self.paths:
            del self.paths[obj_id]

        # Find and update the block
        block = next((block for block in self.get_blocks()
                     if str(block.block_obj.__hash__()) == str(obj_id) or 
                     block.block_obj.contains(obj_id)), None)
        
        if block:
            if str(block.block_obj.__hash__()) == str(obj_id):
                block.block_obj.deallocate()
                self.memory["used_ram_mem"] -= block.block_obj.mem
            else:
                block.block_obj.remove_object(obj_id)
                # Update memory for containing pools and arenas
                for arena in self.memory["arenas"].itertuples():
                    for pool in arena.pools.itertuples():
                        if any(b.block_obj == block.block_obj for b in pool.blocks.itertuples()):
                            pool.pool_obj.mem -= obj_size
                            arena.arena_obj.mem -= obj_size
                            break
        else:
            print(f"Object with ID '{obj_id}' not found.")
            return

        print(f"Updated RAM Memory: {self.memory['used_ram_mem']}")

    def add_arena(self, arena: Arena) -> None:
        arena_count = len(self.memory["arenas"]) + 1
        arena_name = f"Arena {arena_count}"
        new_arena = pd.DataFrame([{
            "arena_obj": arena,
            "arena_name": arena_name,
            "pools": pd.DataFrame(columns=["pool_obj", "pool_name", "blocks"])
        }])
        self.memory["arenas"] = pd.concat([self.memory["arenas"], new_arena], ignore_index=True)
        print(f"Added Arena: {arena_name}")

    def add_pool(self, arena_name: str, pool: Pool) -> None:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if not arena_index.empty:
            arena_index = arena_index[0]
            pool_count = len(self.memory["arenas"].at[arena_index, "pools"]) + 1
            new_pool = pd.DataFrame([{
                "pool_obj": pool,
                "pool_name": f"pool {pool_count}",
                "blocks": pd.DataFrame(columns=["block_obj"])
            }])
            self.memory["arenas"].at[arena_index, "pools"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"], new_pool], ignore_index=True)
            print(f"Added Pool: pool {pool_count} to Arena: {arena_name}")
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

    def add_block(self, arena_name: str, pool_name: str, block: Block) -> None:
        """Add a block to a specified pool in an arena."""
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index[0]
        pool_index = self.memory["arenas"].at[arena_index, "pools"][
            self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name
        ].index[0]
        pool = self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "pool_obj"]

        if pool.mem + block.mem > pool.max_mem:
            new_pool = Pool(0)
            self.add_pool(arena_name, new_pool)
            pool_name = f"pool {len(self.memory['arenas'].at[arena_index, 'pools'])}"
            print(f"Created new Pool: {pool_name} in Arena: {arena_name}")

        # Try to find and reuse a free block
        free_block = self.find_free_block(arena_name, pool_name)
        if free_block:
            free_block.mem = block.mem
            free_block.allocate()
            if block.mem > 0:
                self.memory["used_ram_mem"] += block.mem
            print(f"Reused free block in Pool: {pool_name} in Arena: {arena_name}")
        else:
            blocks = self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"]
            new_block = {"block_obj": block}
            self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"] = pd.concat(
                [blocks, pd.DataFrame([new_block])], ignore_index=True
            )
            pool.mem += block.mem
            block.allocate()
            if block.mem > 0:
                self.memory["used_ram_mem"] += block.mem
            print(f"Added new block to Pool: {pool_name} in Arena: {arena_name}")

    def calculate_arena_memory(self, arena_name: str) -> int:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if arena_index.empty:
            raise ValueError(f"Arena {arena_name} does not exist.")
        arena_index = arena_index[0]
        return sum(pool.pool_obj.mem for pool in self.memory["arenas"].at[arena_index, "pools"].itertuples())

    def calculate_pool_memory(self, arena_name: str, pool_name: str) -> int:
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if arena_index.empty:
            raise ValueError(f"Arena {arena_name} does not exist.")
        arena_index = arena_index[0]
        pool_index = self.memory["arenas"].at[arena_index, "pools"][self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name].index
        if pool_index.empty:
            raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        pool_index = pool_index[0]
        return sum(block.block_obj.mem for block in self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"].itertuples())

    def fill_ram(self, obj_mem):
        remaining_memory = obj_mem
        while remaining_memory > 0:
            if self.memory["arenas"].empty or self.memory["arenas"].iloc[-1]["arena_obj"].mem >= self.memory["arenas"].iloc[-1]["arena_obj"].max_mem:
                new_arena = Arena(0)
                self.add_arena(new_arena)
            last_arena = self.memory["arenas"].iloc[-1]
            if last_arena["arena_obj"].mem < last_arena["arena_obj"].max_mem:
                mem_to_add = min(remaining_memory, last_arena["arena_obj"].max_mem - last_arena["arena_obj"].mem)
                last_arena["arena_obj"].add_mem(mem_to_add)
                remaining_memory -= mem_to_add
                print(f"Filling pools in {last_arena['arena_name']} with {mem_to_add} memory")
                self.fill_pools(last_arena["arena_obj"], mem_to_add)

            else:
                raise MemoryError("Not enough memory available in the arenas to allocate the object.")
            print(f"Total Arena Memory in RAM: {last_arena['arena_obj'].mem}")
            print(f"Remaining Memory in RAM: {self.memory['ram_mem'] - self.memory['used_ram_mem']}")

        self.memory["used_ram_mem"] += obj_mem
        print(f"Used RAM Memory: {self.memory['used_ram_mem']}")

    def fill_pools(self, arena, obj_mem):
        print(f"Filling pools in {arena} with {obj_mem} memory")
        remaining_memory = obj_mem
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_obj"] == arena].index[0]

        while remaining_memory > 0:
            if self.memory["arenas"].at[arena_index, "pools"].empty or self.memory["arenas"].at[arena_index, "pools"].iloc[-1]["pool_obj"].mem >= self.memory["arenas"].at[arena_index, "pools"].iloc[-1]["pool_obj"].max_mem:
                new_pool = Pool(0)
                pool_count = len(self.memory["arenas"].at[arena_index, "pools"]) + 1
                new_pool_df = pd.DataFrame([{
                    "pool_obj": new_pool,
                    "pool_name": f"pool {pool_count}",
                    "blocks": pd.DataFrame(columns=["block_obj"])
                }])
                self.memory["arenas"].at[arena_index, "pools"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"], new_pool_df], ignore_index=True)
                print(f"Added Pool: pool {pool_count} to Arena: {arena}")

            last_pool = self.memory["arenas"].at[arena_index, "pools"].iloc[-1]
            if last_pool["pool_obj"].mem < last_pool["pool_obj"].max_mem:
                mem_to_add = min(remaining_memory, last_pool["pool_obj"].max_mem - last_pool["pool_obj"].mem)
                last_pool["pool_obj"].add_mem(mem_to_add)
                remaining_memory -= mem_to_add
                print(f"Filling blocks in {last_pool['pool_name']} with {mem_to_add} memory")
                self.fill_blocks(last_pool["pool_obj"], mem_to_add, arena_index)

            else:
                raise MemoryError("Not enough memory available in the pools to allocate the object.")

        print(f"Total Pool Memory in Arena: {arena.mem}")

    def fill_blocks(self, pool, obj_mem, arena_index):
        remaining_memory = obj_mem
        pool_index = self.memory["arenas"].at[arena_index, "pools"][self.memory["arenas"].at[arena_index, "pools"]["pool_obj"] == pool].index[0]

        while remaining_memory > 0:
            if self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"].empty or self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"].iloc[-1]["block_obj"].mem >= self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"].iloc[-1]["block_obj"].max_mem:
                new_block = Block(0)
                new_block_df = pd.DataFrame([{
                    "block_obj": new_block
                }])
                self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"], new_block_df], ignore_index=True)

            last_block = self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"].iloc[-1]
            if last_block["block_obj"].mem < last_block["block_obj"].max_mem:
                mem_to_add = min(remaining_memory, last_block["block_obj"].max_mem - last_block["block_obj"].mem)
                last_block["block_obj"].add_mem(mem_to_add)
                remaining_memory -= mem_to_add
            else:
                raise MemoryError("Not enough memory available in the blocks to allocate the object.")

        print(f"Total Block Memory in Pool: {pool.mem}")

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

    def get_memory_stats(self) -> dict:
        """
        Get statistics about memory usage.
        Returns a dictionary containing memory usage statistics.
        """
        return {
            "total_arenas": len(self.memory["arenas"]),
            "total_pools": sum(len(arena.pools) for arena in self.memory["arenas"].itertuples()),
            "used_memory": self.memory["used_ram_mem"],
            "free_memory": self.memory["ram_mem"] - self.memory["used_ram_mem"],
            "free_blocks": sum(1 
                          for arena in self.memory["arenas"].itertuples()
                          for pool in arena.pools.itertuples()
                          for block in pool.blocks.itertuples()
                          if block.block_obj.is_free)
        }

    def find_free_block(self, arena_name: str, pool_name: str):
        """Find first free block in specified pool."""
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index[0]
        pool_index = self.memory["arenas"].at[arena_index, "pools"][
            self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name
        ].index[0]
        blocks = self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"]
        return next((row["block_obj"] for _, row in blocks.iterrows() if row["block_obj"].is_free), None)

# Demo
if __name__ == "__main__":
    # Initialize RAM with a specific amount of memory
    ram = RAM(memory=1_000_000)  # 1,000,000 units of RAM

    # Create a memory manager instance
    mem_manager = MemManager(ram=ram)

    # Add various objects to the memory manager
    objects_to_add = [42, "hello", 3.14, [1, 2, 3], {"key": "value"}]  # Different data types
    for obj in objects_to_add:
        mem_manager.add_object(obj)

    # Print the current state of the memory manager
    print(mem_manager)

    # Check the total memory in arenas
    total_arena_mem = sum(arena.arena_obj.mem for arena in mem_manager.memory["arenas"].itertuples())
    print(f"Total Arena Memory: {total_arena_mem}")

    print(mem_manager.object_index)
    # Remove first object from each arena
    for arena_name, objects in mem_manager.object_index.items():
        if objects:  # Check if arena has any objects
            first_obj_id = next(iter(objects))  # Get first object ID
            mem_manager.remove_object(first_obj_id)
    print(mem_manager.object_index)
    print(mem_manager.memory["arenas"].iloc[0]["arena_obj"].mem)
    print(mem_manager)


