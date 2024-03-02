from pydantic import BaseModel, Field, ValidationError, validator, field_validator
from typing import Annotated, Any, Dict, List, Optional, Set, Union
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

    def all_attributes(self) -> Dict[str, 'Attribute']:
        attributes = {}
        for attribute_name, attribute_value in self.__dict__.items():
            if isinstance(attribute_value, Attribute):
                attributes[attribute_name] = attribute_value
            elif isinstance(attribute_value, Entity):
                nested_attributes = attribute_value.all_attributes()
                attributes.update(nested_attributes)
        return attributes