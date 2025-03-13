"""Test script to check hashability of Pydantic models"""
from pydantic import BaseModel, Field, ConfigDict

class SimpleModel(BaseModel):
    """A simple Pydantic model without any special configuration"""
    x: int
    
class HashableModel(BaseModel):
    """A Pydantic model configured to be hashable"""
    x: int
    model_config = ConfigDict(frozen=True)
    
class TestEqualityModel(BaseModel):
    """A model that overrides __eq__"""
    x: int
    
    def __eq__(self, other):
        if not isinstance(other, TestEqualityModel):
            return False
        return self.x == other.x
        
class CustomHashModel(BaseModel):
    """A model with custom hash implementation"""
    x: int
    
    def __hash__(self):
        return hash(self.x)
        
    def __eq__(self, other):
        if not isinstance(other, CustomHashModel):
            return False
        return self.x == other.x
        
# Test regular model
try:
    m1 = SimpleModel(x=1)
    hash(m1)
    print("SimpleModel is hashable")
except TypeError as e:
    print(f"SimpleModel is not hashable: {e}")
    
# Test frozen model
try:
    m2 = HashableModel(x=1)
    hash(m2)
    print("HashableModel is hashable")
except TypeError as e:
    print(f"HashableModel is not hashable: {e}")
    
# Test model with __eq__ override
try:
    m3 = TestEqualityModel(x=1)
    hash(m3)
    print("TestEqualityModel is hashable")
except TypeError as e:
    print(f"TestEqualityModel is not hashable: {e}")
    
# Test model with custom hash
try:
    m4 = CustomHashModel(x=1)
    hash(m4)
    print("CustomHashModel is hashable")
except TypeError as e:
    print(f"CustomHashModel is not hashable: {e}")
    
# Test putting in a set
try:
    set1 = {SimpleModel(x=1)}
    print("Can put SimpleModel in a set")
except TypeError as e:
    print(f"Cannot put SimpleModel in a set: {e}")
    
try:
    set2 = {HashableModel(x=1)}
    print("Can put HashableModel in a set")
except TypeError as e:
    print(f"Cannot put HashableModel in a set: {e}")
    
try:
    set3 = {TestEqualityModel(x=1)}
    print("Can put TestEqualityModel in a set")
except TypeError as e:
    print(f"Cannot put TestEqualityModel in a set: {e}")
    
try:
    set4 = {CustomHashModel(x=1)}
    print("Can put CustomHashModel in a set")
except TypeError as e:
    print(f"Cannot put CustomHashModel in a set: {e}")