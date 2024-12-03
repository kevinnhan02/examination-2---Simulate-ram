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
        self.free_blocks = []

    def generate_unique_id(self) -> str:
        return str(uuid.uuid4())

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
        arena_index = self.memory["arenas"][self.memory["arenas"]["arena_name"] == arena_name].index
        if not arena_index.empty:
            arena_index = arena_index[0]
            pool_index = self.memory["arenas"].at[arena_index, "pools"][self.memory["arenas"].at[arena_index, "pools"]["pool_name"] == pool_name].index
            if not pool_index.empty:
                pool_index = pool_index[0]
                pool = self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "pool_obj"]
                if pool.mem + block.mem > pool.max_mem:
                    # Pool is full, create a new pool
                    new_pool = Pool(0)
                    self.add_pool(arena_name, new_pool)
                    pool_name = f"pool {len(self.memory['arenas'].at[arena_index, 'pools'])}"
                new_block = {
                    "block_obj": block
                }
                self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"] = pd.concat([self.memory["arenas"].at[arena_index, "pools"].at[pool_index, "blocks"], pd.DataFrame([new_block])], ignore_index=True)
                pool.mem += block.mem
                print(f"Added Block to Pool: {pool_name} in Arena: {arena_name}")
            else:
                raise ValueError(f"Pool {pool_name} does not exist in Arena {arena_name}.")
        else:
            raise ValueError(f"Arena {arena_name} does not exist.")

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

# Demo
if __name__ == "__main__":
    ram = RAM(memory=1_000_000)  # 1,000,000 units of RAM
    mem_manager = MemManager(ram=ram)

    # Allocate 50,000 units of memory
    obj_mem = 500000
    mem_manager.fill_ram(obj_mem)

    # Print the memory manager state
    print(mem_manager)

    # Check the total memory in arenas
    total_arena_mem = sum(arena.arena_obj.mem for arena in mem_manager.memory["arenas"].itertuples())
    print(f"Total Arena Memory: {total_arena_mem}")

    # Check if pools and blocks have been created within the arenas
    for arena in mem_manager.memory["arenas"].itertuples():
        print(f"Arena: {arena.arena_name}, Pools: {len(arena.pools)}")
        for pool in arena.pools.itertuples():
            print(f"  Pool: {pool.pool_name}, Blocks: {len(pool.blocks)}")
        print(f"Remaining Memory in {arena.arena_name}: {arena.arena_obj.max_mem - arena.arena_obj.mem}")

    print(mem_manager.memory["arenas"].iloc[0]["arena_obj"].mem)
    print(f"Number of Pools in the first Arena: {len(mem_manager.memory['arenas'].iloc[0]['pools'])}")