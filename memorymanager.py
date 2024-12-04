from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from Schemas import Base, MemRam, Arena, Pool, Block, Ledger, StoredObject
from sqlalchemy.sql import func
import helpers.listeners
import json
import hashlib
import re


class MemManager:
    def __init__(self, db_url: str) -> None:

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

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

    def add_pool(self, arena: Arena) -> Pool:
        """Create a new pool and add it to the arena table"""
        new_pool = Pool()
        new_pool.arena = arena
        self.session.add(new_pool)
        self.session.commit()
        return new_pool

    def add_block(self, pool: Pool) -> Block:
        """Create a new block and add it to the pool table"""
        new_block = Block()
        new_block.pool = pool
        self.session.add(new_block)
        self.session.commit()
        return new_block

    def generate_object_id(self, identifier):
        """Generate a consistent object_id for a given identifier."""
        if isinstance(identifier, str):
            # Check if the string is already a SHA-256 hash
            if re.fullmatch(r'[a-f0-9]{64}', identifier):
                return identifier
            else:
                # Assume the string is an object and hash it
                serialized_obj = json.dumps(identifier, sort_keys=True)
                return hashlib.sha256(serialized_obj.encode('utf-8')).hexdigest()
        else:
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
        stored_object = self.session.query(StoredObject).filter(StoredObject.object_id == object_id).first()
        if not stored_object:
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
                arena = self.session.query(Arena).filter(Arena.max_mem - Arena.mem > 0).first()
                if not arena:
                    arena = self.add_arena()

                # Check if there are enough pools in the arena
                pool = self.session.query(Pool).filter(Pool.arena_id == arena.id, Pool.max_mem - Pool.mem > 0).first()
                if not pool:
                    pool = self.add_pool(arena)

                # Create a new block in the pool
                block = self.add_block(pool)

                # Calculate how much space is left in the block
                available_space = block.max_mem - block.mem
                to_allocate = min(remaining_size, available_space)

                # Add part of the object to the block
                block.mem += to_allocate
                block.is_free = 0 if block.mem == block.max_mem else 1
                remaining_size -= to_allocate
                blocks_to_update.append(block)

                # Add a post to the ledger
                ledger_entry = Ledger(
                    arena_id=block.pool.arena_id,
                    pool_id=block.pool_id,
                    block_id=block.id,
                    object_id=object_id,
                    allocated_mem=to_allocate
                )
                self.session.add(ledger_entry)

        # Batch commit
        self.session.bulk_save_objects(blocks_to_update)
        self.session.commit()

        print(f"Allocated {obj_size} bytes for object across multiple blocks.")

    def free_memory_for_object(self, identifier) -> None:
        """Free memory for an object by updating the ledger and blocks."""
        # Check if the identifier is an object or a string
        object_id = self.generate_object_id(identifier)

        print(f"Freeing memory for object with identifier: {object_id}")

        # Get all ledger entries for the given object_id
        ledger_entries = self.session.query(Ledger).filter(Ledger.object_id == object_id).all()

        for ledger_entry in ledger_entries:
            # Get the corresponding block
            block = self.session.query(Block).filter(Block.id == ledger_entry.block_id).first()

            if block:
                # Free memory in the block
                allocated_mem = ledger_entry.allocated_mem
                block.mem -= allocated_mem
                # Mark the block as dirty to trigger the listener
                block.is_free = 0 if block.mem == block.max_mem else 1

        # Delete all ledger entries for the given object_id
        self.session.query(Ledger).filter(Ledger.object_id == object_id).delete()
        self.session.query(StoredObject).filter(StoredObject.object_id == object_id).delete()

        # Save the changes
        self.session.commit()