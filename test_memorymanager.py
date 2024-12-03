import unittest
from memorymanager import MemManager
from arena import Arena
from pool import Pool
from block import Block
from ram import RAM
import pandas as pd

class TestMemManager(unittest.TestCase):
    def setUp(self):
        # Create a RAM instance with a specific amount of memory
        self.ram = RAM(memory=1_000_000)  # 1,000,000 units of RAM
        # Create a MemManager instance
        self.mem_manager = MemManager(ram=self.ram)

    def test_add_arena(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        self.assertEqual(len(self.mem_manager.memory["arenas"]), 1)
        self.assertEqual(self.mem_manager.memory["arenas"].iloc[0]["arena_name"], "Arena 1")

    def test_add_pool(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        self.assertEqual(len(self.mem_manager.memory["arenas"].iloc[0]["pools"]), 1)
        self.assertEqual(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["pool_name"], "pool 1")

    def test_add_block(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(len(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"]), 1)

    def test_calculate_arena_memory(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(self.mem_manager.calculate_arena_memory("Arena 1"), block.mem)

    def test_calculate_pool_memory(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        block = Block(0)
        self.mem_manager.add_block("Arena 1", "pool 1", block)
        self.assertEqual(self.mem_manager.calculate_pool_memory("Arena 1", "pool 1"), block.mem)

    def test_fill_ram(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)
        self.assertEqual(self.mem_manager.memory["used_ram_mem"], obj_mem)
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)
        total_arena_mem = sum(arena.arena_obj.mem for arena in self.mem_manager.memory["arenas"].itertuples())
        self.assertEqual(total_arena_mem, obj_mem)
        for arena in self.mem_manager.memory["arenas"].itertuples():
            for pool in arena.pools.itertuples():
                self.assertGreater(len(pool.blocks), 0)

    def test_fill_arena(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)

        # Check that at least one arena has been created
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        # Verify that the total memory in the arena matches the allocated memory
        total_arena_mem = sum(arena.arena_obj.mem for arena in self.mem_manager.memory["arenas"].itertuples())
        self.assertEqual(total_arena_mem, obj_mem)

    def test_fill_pool(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)

        # Check that at least one arena has been created
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        # Check that pools have been created in the arenas
        for arena in self.mem_manager.memory["arenas"].itertuples():
            self.assertGreater(len(arena.pools), 0)

            # Verify that the total memory in the pools matches the allocated memory
            total_pool_mem = sum(pool.pool_obj.mem for pool in arena.pools.itertuples())
            self.assertEqual(total_pool_mem, arena.arena_obj.mem)


    def test_arena_has_pools_column(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        self.assertIn("pools", self.mem_manager.memory["arenas"].columns)
        self.assertIsInstance(self.mem_manager.memory["arenas"].iloc[0]["pools"], pd.DataFrame)

    def test_pool_has_blocks_column(self):
        arena = Arena(0)
        self.mem_manager.add_arena(arena)
        pool = Pool(0)
        self.mem_manager.add_pool("Arena 1", pool)
        self.assertIn("blocks", self.mem_manager.memory["arenas"].iloc[0]["pools"].columns)
        self.assertIsInstance(self.mem_manager.memory["arenas"].iloc[0]["pools"].iloc[0]["blocks"], pd.DataFrame)

    def test_fill_ram_creates_pools(self):
        obj_mem = 50000  # 50,000 units of memory
        self.mem_manager.fill_ram(obj_mem)
        self.assertEqual(self.mem_manager.memory["used_ram_mem"], obj_mem)
        self.assertGreater(len(self.mem_manager.memory["arenas"]), 0)

        total_pools = 0
        for arena in self.mem_manager.memory["arenas"].itertuples():
            total_pools += len(arena.pools)

        # Assuming each pool can hold a certain amount of memory, we can calculate the expected number of pools
        pool_capacity = Pool().max_mem
        expected_pools = (obj_mem + pool_capacity - 1) // pool_capacity  # Ceiling division

        self.assertEqual(total_pools, expected_pools)
        for arena in self.mem_manager.memory["arenas"].itertuples():
            for pool in arena.pools.itertuples():
                self.assertGreater(len(pool.blocks), 0)

if __name__ == "__main__":
        unittest.main()