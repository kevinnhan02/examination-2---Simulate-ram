"""Memory Manager for managing memory allocation and deallocation.
This is meant to mimic python's memory management system.
"""

import json
import hashlib
import re
import logging
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from database_models import Base, MemRam, Arena, Pool, Block, Ledger, StoredObject
import helpers.listeners  # pylint: disable=unused-import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MemManager:
    """
    Memory Manager class for managing memory allocation and deallocation.

    Parameters
    ----------
    db_url : str
        The database URL for connecting to the SQLite database.
    """

    def __init__(self, db_url: str) -> None:
        """
        Initialize the memory manager with a SQLite database URL.

        Parameters
        ----------
        db_url : str
            The database URL for connecting to the SQLite database.
        """
        try:
            self.engine = create_engine(db_url)
            Base.metadata.create_all(self.engine)
            session = sessionmaker(bind=self.engine)
            self.session = session()

            # Skapa en ny MemRam-post
            self.memram = MemRam()
            self.session.add(self.memram)
            self.session.commit()
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error initializing MemManager: %s", exc)
            raise

    def add_arena(self) -> Arena:
        """
        Create a new arena and add it to the MemRam table.

        Returns
        -------
        Arena
            The newly created Arena object.
        """
        try:
            new_arena = Arena()
            new_arena.memram = self.memram
            self.session.add(new_arena)
            self.session.commit()
            return new_arena
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error adding arena: %s", exc)
            self.session.rollback()
            raise

    def add_pool(self, target_arena: Arena) -> Pool:
        """
        Create a new pool and add it to the arena table.

        Parameters
        ----------
        target_arena : Arena
            The target Arena object to which the pool will be added.

        Returns
        -------
        Pool
            The newly created Pool object.
        """
        try:
            new_pool = Pool()
            new_pool.arena = target_arena
            self.session.add(new_pool)
            self.session.commit()
            return new_pool
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error adding pool: %s", exc)
            self.session.rollback()
            raise

    def add_block(self, target_pool: Pool) -> Block:
        """
        Create a new block and add it to the pool table.

        Parameters
        ----------
        target_pool : Pool
            The target Pool object to which the block will be added.

        Returns
        -------
        Block
            The newly created Block object.
        """
        try:
            new_block = Block()
            new_block.pool = target_pool
            self.session.add(new_block)
            self.session.commit()
            return new_block
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error adding block: %s", exc)
            self.session.rollback()
            raise

    def generate_object_id(self, identifier):
        """
        Generate a consistent object_id for a given identifier.

        Parameters
        ----------
        identifier : str or object
            The identifier for which the object_id will be generated.

        Returns
        -------
        str
            The generated object_id as a SHA-256 hash.
        """
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
        """
        Allocate memory for an object by creating necessary arenas, pools, and blocks.

        Parameters
        ----------
        obj_instance : object
            The object instance for which memory will be allocated.

        Raises
        ------
        MemoryError
            If there is not enough memory to allocate the object.
        """
        try:
            obj_size = obj_instance.__sizeof__()

            # Create a unique and consistent identifier for the object
            object_id = self.generate_object_id(obj_instance)

            if self.memram.max_mem < obj_size:
                raise MemoryError("Not enough memory to allocate object.")

            remaining_size = obj_size
            blocks_to_update = []

            # Check if the object is already stored
            if self.is_object_stored(object_id):
                logger.info("Object with identifier %s already exists in the database.", object_id)
                return

            logger.info("Object with identifier %s stored in the database.", object_id)

            # Store the object in the StoredObject table
            self.store_object(object_id, obj_instance)

            # Get blocks that have enough space for the object
            while remaining_size > 0:
                suitable_block = self.find_suitable_block()

                if suitable_block:
                    remaining_size = \
                        self.allocate_to_block(suitable_block, remaining_size,\
                                                blocks_to_update, object_id)
                else:
                    remaining_size = \
                    self.allocate_to_new_block(remaining_size,\
                                                blocks_to_update, object_id)

            # Batch commit
            self.session.bulk_save_objects(blocks_to_update)
            self.session.commit()

            logger.info("Allocated %d bytes for object across multiple blocks.", obj_size)
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error allocating memory for object: %s", exc)
            self.session.rollback()
            raise
        except MemoryError as exc:  # pylint: disable=redefined-outer-name
            logger.error("MemoryError: %s", exc)
            raise

    def is_object_stored(self, object_id: str) -> bool:
        """
        Check if the object is already stored in the database.

        Parameters
        ----------
        object_id : str
            The unique identifier of the object.

        Returns
        -------
        bool
            True if the object is already stored, False otherwise.
        """
        stored_object = self.session.query(StoredObject).filter(
            StoredObject.object_id == object_id).first()
        return stored_object is not None

    def store_object(self, object_id: str, obj_instance: object) -> None:
        """
        Store the object in the StoredObject table.

        Parameters
        ----------
        object_id : str
            The unique identifier of the object.
        obj_instance : object
            The object instance to be stored.
        """
        stored_object = StoredObject(object_id=object_id, object_data=obj_instance)
        self.session.add(stored_object)
        self.session.commit()

    def find_suitable_block(self) -> Block:
        """
        Find a suitable block that has enough space for the object.

        Returns
        -------
        Block
            A block that has enough space for the object, or None if no suitable block is found.
        """
        return self.session.query(Block).filter(
            Block.is_free == 1,
            Block.max_mem - Block.mem > 0
        ).first()

    def allocate_to_block(self, target_block: Block, remaining_size: int,
                        target_blocks_to_update: list, object_id: str) -> int:
        """
        Allocate part of the object to the target_block.

        Parameters
        ----------
        target_block : Block
            The block to which part of the object will be allocated.
        remaining_size : int
            The remaining size of the object to be allocated.
        target_blocks_to_update : list
            The list of blocks to be updated.
        object_id : str
            The unique identifier of the object.

        Returns
        -------
        int
            The remaining size of the object to be allocated.
        """
        available_space = target_block.max_mem - target_block.mem
        to_allocate = min(remaining_size, available_space)

        target_block.mem += to_allocate
        target_block.is_free = 0 if target_block.mem == target_block.max_mem else 1
        remaining_size -= to_allocate
        target_blocks_to_update.append(target_block)

        ledger_entry = Ledger(
            arena_id=target_block.pool.arena_id,
            pool_id=target_block.pool_id,
            block_id=target_block.id,
            object_id=object_id,
            allocated_mem=to_allocate
        )
        self.session.add(ledger_entry)

        return remaining_size

    def allocate_to_new_block(self, remaining_size: int,
                            blocks_to_update: list, object_id: str) -> int:
        """
        Allocate part of the object to a new block in a new pool and arena if necessary.

        Parameters
        ----------
        remaining_size : int
            The remaining size of the object to be allocated.
        blocks_to_update : list
            The list of blocks to be updated.
        object_id : str
            The unique identifier of the object.

        Returns
        -------
        int
            The remaining size of the object to be allocated.
        """
        new_arena = self.session.query(Arena).filter(
            Arena.max_mem - Arena.mem > 0).first()
        if not new_arena:
            new_arena = self.add_arena()

        new_pool = self.session.query(Pool).filter(
            Pool.arena_id == new_arena.id,
            Pool.max_mem - Pool.mem > 0).first()
        if not new_pool:
            new_pool = self.add_pool(new_arena)

        new_block = self.add_block(new_pool)

        available_space = new_block.max_mem - new_block.mem
        to_allocate = min(remaining_size, available_space)

        new_block.mem += to_allocate
        new_block.is_free = 0 if new_block.mem == new_block.max_mem else 1
        remaining_size -= to_allocate
        blocks_to_update.append(new_block)

        ledger_entry = Ledger(
            arena_id=new_block.pool.arena_id,
            pool_id=new_block.pool_id,
            block_id=new_block.id,
            object_id=object_id,
            allocated_mem=to_allocate
        )
        self.session.add(ledger_entry)

        return remaining_size

    def free_memory_for_object(self, identifier) -> None:
        """
        Free memory for an object by updating the ledger and blocks.

        Parameters
        ----------
        identifier : str or object
            The identifier for which memory will be freed.
        """
        try:
            # Generate the object_id from the identifier
            object_id = self.generate_object_id(identifier)

            logger.info("Freeing memory for object with identifier: %s", object_id)

            # Get all ledger entries for the given object_id
            ledger_entries = self.session.query(Ledger).filter(
                Ledger.object_id == object_id).all()

            for ledger_entry in ledger_entries:
                # Get the corresponding block
                target_block = self.session.query(Block).filter(
                    Block.id == ledger_entry.block_id).first()

                if target_block:
                    allocated_mem = ledger_entry.allocated_mem
                    target_block.mem -= allocated_mem
                    # Mark the block as dirty to trigger the listener
                    target_block.is_free = 0 if target_block.mem == target_block.max_mem else 1

            # Delete all ledger entries for the given object_id
            self.session.query(Ledger).filter(Ledger.object_id == object_id).delete()
            self.session.query(StoredObject).filter(StoredObject.object_id == object_id).delete()

            # Save the changes
            self.session.commit()

            logger.info("Freed memory for object with identifier: %s", object_id)
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error freeing memory for object: %s", exc)
            self.session.rollback()
            raise

    def print_memory_statistics(self):
        """
        Print memory usage statistics.

        Logs the total number of arenas, pools, blocks, total allocated memory,
        and total free memory.
        """
        try:
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
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error printing memory statistics: %s", exc)
            raise

    def get_object(self, identifier):
        """
        Retrieve an object from the database using its identifier.

        Parameters
        ----------
        identifier : str or object
            The identifier for which the object will be retrieved.

        Returns
        -------
        object or None
            The retrieved object if found, otherwise None.
        """
        try:
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
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error retrieving object: %s", exc)
            raise
    def manual_garbage_collection(self) -> None:
        """
        Remove all unused blocks, pools, and arenas.

        This method identifies and removes blocks that are not used,
        pools that are empty, and arenas that are empty.

        Raises
        ------
        SQLAlchemyError
            If there is an error during the removal of unused resources.
        """
        try:
            # Remove unused blocks
            unused_blocks = self.session.query(Block).\
                filter(Block.is_free == 1, Block.mem == 0).all()
            for target_block in unused_blocks:
                self.session.delete(target_block)
                logger.info("Removed unused block with ID: %d", target_block.id)

            # Remove empty pools
            empty_pools = self.session.query(Pool).filter(~Pool.blocks.any()).all()
            for target_pool in empty_pools:
                self.session.delete(target_pool)
                logger.info("Removed empty pool with ID: %d", target_pool.id)

            # Remove empty arenas
            empty_arenas = self.session.query(Arena).filter(~Arena.pools.any()).all()
            for target_arena in empty_arenas:
                self.session.delete(target_arena)
                logger.info("Removed empty arena with ID: %d", target_arena.id)

            # Save the changes
            self.session.commit()
            logger.info("Removed all unused resources.")
        except SQLAlchemyError as exc:  # pylint: disable=redefined-outer-name
            logger.error("Error removing unused resources: %s", exc)
            self.session.rollback()
            raise

if __name__ == "__main__":
    try:
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

        # print("\n**retrieved objects**\n"
        #       f"OBJ1: {retrieved_obj1}\n"
        #       f"obj2: {retrieved_obj2}")

        print("\n**before freeing memory**\n")
        memory_manager.print_memory_statistics()

        # Free memory for the first object
        memory_manager.free_memory_for_object(OBJ1)

        # Free memory for the second object
        memory_manager.free_memory_for_object(obj2)

        # Print final memory statistics
        print("\n**after freeing memory**\n")
        memory_manager.print_memory_statistics()

        print("\n**nmanual garbage collection**\n")

        memory_manager.manual_garbage_collection()

        memory_manager.print_memory_statistics()

        print("\n**reallocate memory for object after garbage collection**\n")

        memory_manager.allocate_memory_for_object(OBJ1)

        memory_manager.print_memory_statistics()
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("An error occurred: %s", exc)
