"""
Debug script to isolate the address resolution issue.

This script tests the specific functionality that's failing in the distributed addressing examples.
"""

from typing import Union, List
from pydantic import Field
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.functional_api import get
from abstractions.ecs.ecs_address_parser import ECSAddressParser

# Define test entities with proper Pydantic fields
class Student(Entity):
    name: str = Field(default="")
    gpa: float = Field(default=0.0)

class Course(Entity):
    name: str = Field(default="")
    credits: int = Field(default=0)
    grade: str = Field(default="")

@CallableRegistry.register("create_transcript_test")
def create_transcript_test(name: str, gpa: float, courses: list) -> Course:
    """Test function that should handle string addresses automatically."""
    print(f"  Function received: name={name} (type: {type(name)})")
    print(f"  Function received: gpa={gpa} (type: {type(gpa)})")
    print(f"  Function received: courses={courses} (type: {type(courses)})")
    
    return Course(name=f"Transcript for {name}", credits=len(courses), grade=f"GPA: {gpa}")

def main():
    print("=== Debug Address Resolution ===\n")
    
    # Step 1: Create and register a student
    student = Student(name="Alice", gpa=3.5)
    student.promote_to_root()
    print(f"1. Created student: {student.name} with GPA {student.gpa}")
    print(f"   Student ID: {student.ecs_id}")
    
    # Step 2: Test direct address resolution
    print(f"\n2. Testing direct address resolution:")
    try:
        student_name = get(f"@{student.ecs_id}.name")
        student_gpa = get(f"@{student.ecs_id}.gpa")
        print(f"   ✅ Direct resolution works: name={student_name}, gpa={student_gpa}")
    except Exception as e:
        print(f"   ❌ Direct resolution failed: {e}")
        return
    
    # Step 3: Test what happens when we pass addresses to functions
    print(f"\n3. Testing what function receives when passed address strings:")
    
    # Create address strings
    name_address = f"@{student.ecs_id}.name"
    gpa_address = f"@{student.ecs_id}.gpa"
    
    print(f"   Addresses to pass:")
    print(f"   - name_address: {name_address}")
    print(f"   - gpa_address: {gpa_address}")
    
    # Test if callable registry automatically resolves addresses
    print(f"\n4. Testing callable registry with address strings:")
    try:
        result = CallableRegistry.execute("create_transcript_test",
            name=name_address,           # String address
            gpa=gpa_address,             # String address  
            courses=["Math", "Physics"]   # Direct value
        )
        
        # Handle Union[Entity, List[Entity]] return type
        if isinstance(result, list):
            actual_result = result[0] if result else None
        else:
            actual_result = result
            
        if actual_result and isinstance(actual_result, Course):
            print(f"   ✅ Function execution succeeded!")
            print(f"   Result: {actual_result}")
            print(f"   Result name: {actual_result.name}")
            print(f"   Result grade: {actual_result.grade}")
        else:
            print(f"   ❌ Unexpected result type: {type(actual_result)}")
            
    except Exception as e:
        print(f"   ❌ Function execution failed: {e}")
        print(f"   Error type: {type(e)}")
        
        # Let's test manual resolution
        print(f"\n5. Testing manual resolution:")
        try:
            resolved_name = get(name_address)
            resolved_gpa = get(gpa_address)
            print(f"   Manual resolution: name={resolved_name}, gpa={resolved_gpa}")
            
            # Try function with resolved values
            result2 = CallableRegistry.execute("create_transcript_test",
                name=resolved_name,
                gpa=resolved_gpa,
                courses=["Math", "Physics"]
            )
            
            # Handle Union[Entity, List[Entity]] return type
            if isinstance(result2, list):
                actual_result2 = result2[0] if result2 else None
            else:
                actual_result2 = result2
                
            if actual_result2 and isinstance(actual_result2, Course):
                print(f"   ✅ Function with manual resolution succeeded!")
                print(f"   Result: {actual_result2}")
                print(f"   Result name: {actual_result2.name}")
                print(f"   Result grade: {actual_result2.grade}")
            else:
                print(f"   ❌ Unexpected result type: {type(actual_result2)}")
            
        except Exception as e2:
            print(f"   ❌ Manual resolution also failed: {e2}")
    
    # Step 4: Test address validation
    print(f"\n6. Testing address validation:")
    print(f"   Is '{name_address}' a valid address? {ECSAddressParser.is_ecs_address(name_address)}")
    print(f"   Is '{gpa_address}' a valid address? {ECSAddressParser.is_ecs_address(gpa_address)}")
    
    # Step 5: Test address parsing
    print(f"\n7. Testing address parsing:")
    try:
        entity_id, field_path = ECSAddressParser.parse_address(name_address)
        print(f"   Parsed name address: entity_id={entity_id}, field_path={field_path}")
        
        entity_id2, field_path2 = ECSAddressParser.parse_address(gpa_address)
        print(f"   Parsed gpa address: entity_id={entity_id2}, field_path={field_path2}")
        
    except Exception as e:
        print(f"   ❌ Address parsing failed: {e}")

if __name__ == "__main__":
    main()