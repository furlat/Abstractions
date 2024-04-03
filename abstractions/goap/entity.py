from pydantic import BaseModel, Field, ValidationError, validator, field_validator, ValidationInfo
from typing import Annotated, Any, Dict, List, Optional, Set, Union, Tuple, Callable
from pydantic.functional_validators import AfterValidator
import uuid


class RegistryHolder:
    _registry: Dict[str, 'RegistryHolder'] = {}
    _types : Set[type] = set()

    @classmethod
    def register(cls, instance: 'RegistryHolder'):
        cls._registry[instance.id] = instance
        cls._types.add(type(instance))

    @classmethod
    def get_instance(cls, instance_id: str):
        return cls._registry.get(instance_id)

    @classmethod
    def all_instances(cls, filter_type=True):
        if filter_type:
            return [instance for instance in cls._registry.values() if isinstance(instance, cls)]
        return list(cls._registry.values())
    @classmethod
    def all_instances_by_type(cls, type: type):
        return [instance for instance in cls._registry.values() if isinstance(instance, type)]
    @classmethod
    def all_types(cls, as_string=True):
        if as_string:
            return [type_name.__name__ for type_name in cls._types]
        return cls._types
        

class Attribute(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the attribute")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the attribute")
    value: Any

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)



class Entity(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the entity")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)
        
    
    @field_validator('*', mode='after')
    def check_attributes_and_entities(cls, v: Any, info: ValidationInfo):
        if info.field_name not in ['id', 'name',"node"] and not isinstance(v, (Attribute, Entity)):
            raise ValueError(f"Attributes must be instances of Attribute or Entity, got {type(v).__name__} for field {info.field_name}")
        return v

    
    def all_attributes(self) -> Dict[str, 'Attribute']:
        attributes = {}
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attributes[attribute_name] = attribute_value
            elif isinstance(attribute_value, Entity):
                nested_attributes = attribute_value.all_attributes()
                attributes.update(nested_attributes)
        return attributes
    

class Statement(BaseModel, RegistryHolder):
    name: str = Field("", description="The name of the statement")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="The unique identifier of the entity")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="The desired attribute conditions for the statement")
    comparisons: Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]] = Field(default_factory=dict, description="The attribute comparisons for the statement")
    callables: List[Callable[[Entity, Entity], bool]] = Field(default_factory=list, description="The generic callables for the statement")

    def __init__(self, **data: Any):
        super().__init__(**data)
        if not self.name:
            self.name = self.__class__.__name__
        self.register(self)

    @classmethod
    def from_entity(cls, entity: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        attributes = entity.all_attributes()
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    @classmethod
    def from_entities(cls, source: Entity, target: Entity, name: Optional[str] = None, conditions: Optional[Dict[str, Any]] = None, comparisons: Optional[Dict[str, Tuple[str, str, Callable[[Any, Any], bool]]]] = None, callables: Optional[List[Callable[[Entity, Entity], bool]]] = None):
        source_attributes = source.all_attributes()
        target_attributes = target.all_attributes()
        attributes = {f"source_{k}": v for k, v in source_attributes.items()}
        attributes.update({f"target_{k}": v for k, v in target_attributes.items()})
        return cls(name=name, conditions=conditions or {}, comparisons=comparisons or {}, callables=callables or [], **attributes)

    def validate_condition(self, entity: Entity) -> bool:
        attributes = entity.all_attributes()
        for attr_name, desired_value in self.conditions.items():
            if attr_name not in attributes or attributes[attr_name].value != desired_value:
                return False
        return True

    def validate_comparisons(self, source: Entity, target: Entity) -> bool:
        for comparison_name, (source_attr, target_attr, comparison_func) in self.comparisons.items():
            source_value = getattr(source, source_attr, None)
            target_value = getattr(target, target_attr, None)
            if source_value is None or target_value is None:
                return False
            elif source_attr == "node" and target_attr == "node":
                if not comparison_func(source_value, target_value):
                    return False
                return True
            elif not comparison_func(source_value.value, target_value.value):
                return False
        return True

    def validate_callables(self, source: Entity, target: Optional[Entity] = None) -> bool:
        for callable_func in self.callables:
            if not callable_func(source, target):
                return False
        return True
    
    def validate_all(self, source: Entity, target: Optional[Entity] = None) -> bool:
        return self.validate_condition(source) and (self.validate_comparisons(source, target) if target else True) and self.validate_callables(source, target)
