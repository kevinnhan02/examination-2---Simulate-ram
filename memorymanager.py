"""Memory Manager for managing memory allocation and deallocation.
This is meant to mimic python's memory management system."""

import json
import hashlib
import re
import logging
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from database_models import Base, MemRam, Arena, Pool, Block, Ledger, StoredObject
import helpers.listeners  # pylint: disable=unused-import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemManager:
    """Memory Manager class for managing memory allocation and deallocation."""
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()

        # Skapa en ny MemRam-post
        self.memram = MemRam()
        self.session.add(self.memram)
        self.session.commit()

    def add_arena(self) -> Arena:
        """Create a new arena and add it to the MemRam table"""
        new_arena = Arena()
        new_arena.memram = self.memram
        self.session.add(new_arena)
        self.session.commit()
        return new_arena

    def add_pool(self, target_arena: Arena) -> Pool:
        """Create a new pool and add it to the arena table"""
        new_pool = Pool()
        new_pool.arena = target_arena
        self.session.add(new_pool)
        self.session.commit()
        return new_pool

    def add_block(self, target_pool: Pool) -> Block:
        """Create a new block and add it to the pool table"""
        new_block = Block()
        new_block.pool = target_pool
        self.session.add(new_block)
        self.session.commit()
        return new_block

    def generate_object_id(self, identifier):
        """Generate a consistent object_id for a given identifier."""
        if isinstance(identifier, str):
            # Check if the string is already a SHA-256 hash
            if re.fullmatch(r'[a-f0-9]{64}', identifier):
                return identifier
            # Assume the string is an object and hash it
            serialized_obj = json.dumps(identifier, sort_keys=True)
            return hashlib.sha256(serialized_obj.encode('utf-8')).hexdigest()
        # Serialize and hash the object
        serialized_obj = json.dumps(identifier, sort_keys=True)
        return hashlib.sha256(serialized_obj.encode('utf-8')).hexdigest()

    def allocate_memory_for_object(self, obj_instance) -> None:
        """Allocate memory for an object by creating necessary arenas, pools and blocks."""
        obj_size = obj_instance.__sizeof__()

        # Create a unique and consistent identifier for the object
        object_id = self.generate_object_id(obj_instance)

        if self.memram.max_mem < obj_size:
            raise MemoryError("Not enough memory to allocate object.")

        remaining_size = obj_size
        blocks_to_update = []

        # Check if the object is already stored
        stored_object = self.session.query(StoredObject).filter(
            StoredObject.object_id == object_id).first()
        if stored_object:
            logger.info("Object with identifier %s already exists in the database.", object_id)
            return

        logger.info("Object with identifier %s stored in the database.", object_id)

        # Store the object in the StoredObject table
        stored_object = StoredObject(object_id=object_id, object_data=obj_instance)
        self.session.add(stored_object)
        self.session.commit()

        # Get blocks that have enough space for the object
        while remaining_size > 0:
            suitable_block = self.session.query(Block).filter(
                Block.is_free == 1,
                Block.max_mem - Block.mem > 0
            ).first()

            if suitable_block:
                # Calculate how much space is left in the block
                available_space = suitable_block.max_mem - suitable_block.mem
                to_allocate = min(remaining_size, available_space)

                # Add part of the object to the block
                suitable_block.mem += to_allocate
                suitable_block.is_free = 0 if suitable_block.mem == suitable_block.max_mem else 1
                remaining_size -= to_allocate
                blocks_to_update.append(suitable_block)

                # Add a post to the ledger
                ledger_entry = Ledger(
                    arena_id=suitable_block.pool.arena_id,
                    pool_id=suitable_block.pool_id,
                    block_id=suitable_block.id,
                    object_id=object_id,
                    allocated_mem=to_allocate
                )
                self.session.add(ledger_entry)
            else:
                # Find an arena with enough space for a new pool
                new_arena = self.session.query(Arena).filter(
                    Arena.max_mem - Arena.mem > 0).first()
                if not new_arena:
                    new_arena = self.add_arena()

                # Check if there are enough pools in the arena
                new_pool = self.session.query(Pool).filter(
                    Pool.arena_id == new_arena.id,
                    Pool.max_mem - Pool.mem > 0).first()
                if not new_pool:
                    new_pool = self.add_pool(new_arena)

                # Create a new block in the pool
                new_block = self.add_block(new_pool)

                # Calculate how much space is left in the block
                available_space = new_block.max_mem - new_block.mem
                to_allocate = min(remaining_size, available_space)

                # Add part of the object to the block
                new_block.mem += to_allocate
                new_block.is_free = 0 if new_block.mem == new_block.max_mem else 1
                remaining_size -= to_allocate
                blocks_to_update.append(new_block)

                # Add a post to the ledger
                ledger_entry = Ledger(
                    arena_id=new_block.pool.arena_id,
                    pool_id=new_block.pool_id,
                    block_id=new_block.id,
                    object_id=object_id,
                    allocated_mem=to_allocate
                )
                self.session.add(ledger_entry)

        # Batch commit
        self.session.bulk_save_objects(blocks_to_update)
        self.session.commit()

        logger.info("Allocated %d bytes for object across multiple blocks.", obj_size)

    def free_memory_for_object(self, identifier) -> None:
        """Free memory for an object by updating the ledger and blocks."""
        # Generate the object_id from the identifier
        object_id = self.generate_object_id(identifier)

        logger.info("Freeing memory for object with identifier: %s", object_id)

        # Get all ledger entries for the given object_id
        ledger_entries = self.session.query(Ledger).filter(
            Ledger.object_id == object_id).all()

        for ledger_entry in ledger_entries:
            # Get the corresponding block
            block_entry = self.session.query(Block).filter(
                Block.id == ledger_entry.block_id).first()

            if block_entry:
                allocated_mem = ledger_entry.allocated_mem
                block_entry.mem -= allocated_mem
                # Mark the block as dirty to trigger the listener
                block_entry.is_free = 0 if block_entry.mem == block_entry.max_mem else 1

        # Delete all ledger entries for the given object_id
        self.session.query(Ledger).filter(Ledger.object_id == object_id).delete()
        self.session.query(StoredObject).filter(StoredObject.object_id == object_id).delete()

        # Save the changes
        self.session.commit()

        logger.info("Freed memory for object with identifier: %s", object_id)

    def print_memory_statistics(self):
        """Print memory usage statistics."""
        # pylint: disable=not-callable
        total_arenas = self.session.query(func.count(Arena.id)).scalar()
        total_pools = self.session.query(func.count(Pool.id)).scalar()
        total_blocks = self.session.query(func.count(Block.id)).scalar()
        total_allocated_mem = self.session.query(func.sum(Block.mem)).scalar() or 0
        total_free_mem = self.memram.max_mem - total_allocated_mem

        logger.info("Memory Statistics: Arenas: %d, Pools: %d, Blocks: %d",
                    total_arenas, total_pools, total_blocks)
        logger.info("Total Allocated Memory: %d bytes", total_allocated_mem)
        logger.info("Total Free Memory: %d bytes", total_free_mem)

    def get_object(self, identifier):
        """Retrieve an object from the database using its identifier."""
        # Generate the object_id from the identifier
        object_id = self.generate_object_id(identifier)

        # Query the StoredObject table for the object
        stored_object = self.session.query(StoredObject).filter(
            StoredObject.object_id == object_id).first()

        if stored_object:
            logger.info("Object with identifier %s retrieved from the database.",
                        object_id)
            return stored_object.object_data
        logger.info("Object with identifier %s not found in the database.",
                    object_id)
        return None

if __name__ == "__main__":
    # Initialize the memory manager with a SQLite database URL
    memory_manager = MemManager("sqlite:///memory_manager_demo.sqlite")

    # Create an arena
    arena = memory_manager.add_arena()

    # Create a pool in the arena
    pool = memory_manager.add_pool(arena)

    # Create a block in the pool
    block = memory_manager.add_block(pool)

    for i in range(2):
        # Allocate memory for an object
        OBJ1 = "Test Object 1" * 1000
        memory_manager.allocate_memory_for_object(OBJ1)

        # Allocate memory for another object
        obj2 = {"key": "value", "number": 42}
        memory_manager.allocate_memory_for_object(obj2)

    # Retrieve the object
    retrieved_obj1 = memory_manager.get_object(OBJ1)

    # Retrieve the second object
    retrieved_obj2 = memory_manager.get_object(obj2)

    print("before freeing memory")
    memory_manager.print_memory_statistics()

    # Free memory for the first object
    memory_manager.free_memory_for_object(OBJ1)

    # Free memory for the second object
    memory_manager.free_memory_for_object(obj2)

    # Print final memory statistics
    print("after freeing memory")
    memory_manager.print_memory_statistics()
