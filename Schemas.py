from sqlalchemy import create_engine, Column, Integer, ForeignKey, String, event, Text,PickleType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()

class MemRam(Base):
    __tablename__ = 'memram'

    id = Column(Integer, primary_key=True)
    max_mem = Column(Integer)
    mem = Column(Integer, default=0)
    arenas = relationship("Arena", back_populates="memram")

    def __init__(self, max_mem=17_179_869_184):
        self.max_mem = max_mem

class Arena(Base):
    __tablename__ = 'arenas'

    id = Column(Integer, primary_key=True)
    max_mem = Column(Integer, default=262144)
    mem = Column(Integer, default=0)
    memram_id = Column(Integer, ForeignKey('memram.id'))
    memram = relationship("MemRam", back_populates="arenas")
    pools = relationship("Pool", back_populates="arena")

    def __init__(self, max_mem=262144):
        self.max_mem = max_mem

class Pool(Base):
    __tablename__ = 'pools'

    id = Column(Integer, primary_key=True)
    max_mem = Column(Integer, default=4096)
    mem = Column(Integer, default=0)
    arena_id = Column(Integer, ForeignKey('arenas.id'))
    arena = relationship("Arena", back_populates="pools")
    blocks = relationship("Block", back_populates="pool")

    def __init__(self, max_mem=4096):
        self.max_mem = max_mem

class Block(Base):
    __tablename__ = 'blocks'

    id = Column(Integer, primary_key=True)
    max_mem = Column(Integer, default=512)
    mem = Column(Integer, default=0)
    pool_id = Column(Integer, ForeignKey('pools.id'))
    pool = relationship("Pool", back_populates="blocks")
    is_free = Column(Integer, default=1)  # 1 for True, 0 for False

    def __init__(self, max_mem=512):
        self.max_mem = max_mem

class StoredObject(Base):
    __tablename__ = 'stored_objects'

    id = Column(Integer, primary_key=True)
    object_id = Column(String, unique=True)
    object_data = Column(PickleType, nullable=False)

class Ledger(Base):
    __tablename__ = 'ledger'

    id = Column(Integer, primary_key=True)
    arena_id = Column(Integer, ForeignKey('arenas.id'))
    pool_id = Column(Integer, ForeignKey('pools.id'))
    block_id = Column(Integer, ForeignKey('blocks.id'))
    object_id = Column(String, ForeignKey('stored_objects.object_id'))  # Reference to the stored object
    allocated_mem = Column(Integer)  # Amount of memory allocated

    arena = relationship("Arena")
    pool = relationship("Pool")
    block = relationship("Block")
    stored_object = relationship("StoredObject", back_populates="ledger_entries")

StoredObject.ledger_entries = relationship("Ledger", back_populates="stored_object")