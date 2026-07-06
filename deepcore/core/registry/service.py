from typing import List, Optional, Union
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import RegistryObject as DBRegistryObject
from deepcore.core.objects.schemas import RegistryObjectCreate, RegistryObjectUpdate

class RegistryService:
    def __init__(self, db: Session):
        self.db = db

    def _get_query(self, object_id_or_uuid: Union[int, str]):
        """Helper to query a registry object by integer ID or string UUID."""
        if isinstance(object_id_or_uuid, int):
            return self.db.query(DBRegistryObject).filter(DBRegistryObject.id == object_id_or_uuid)
        elif isinstance(object_id_or_uuid, str):
            if object_id_or_uuid.isdigit():
                return self.db.query(DBRegistryObject).filter(DBRegistryObject.id == int(object_id_or_uuid))
            return self.db.query(DBRegistryObject).filter(DBRegistryObject.uuid == object_id_or_uuid)
        else:
            raise ValueError("Invalid identifier type")

    def register_object(self, obj_data: RegistryObjectCreate) -> DBRegistryObject:
        """Register a new object in the database."""
        db_obj = DBRegistryObject(**obj_data.model_dump())
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def get_object(self, object_id_or_uuid: Union[int, str]) -> Optional[DBRegistryObject]:
        """Retrieve a specific object by ID or UUID."""
        return self._get_query(object_id_or_uuid).first()

    def list_objects(self, filters: Optional[dict] = None) -> List[DBRegistryObject]:
        """List objects, optionally filtering by specific fields."""
        query = self.db.query(DBRegistryObject)
        if filters:
            for key, value in filters.items():
                if hasattr(DBRegistryObject, key) and value is not None:
                    query = query.filter(getattr(DBRegistryObject, key) == value)
        return query.all()

    def update_object(self, object_id_or_uuid: Union[int, str], update_data: RegistryObjectUpdate) -> DBRegistryObject:
        """Update fields of an existing registry object."""
        db_obj = self._get_query(object_id_or_uuid).first()
        if not db_obj:
            raise ValueError(f"RegistryObject with identifier '{object_id_or_uuid}' not found")
        
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_obj, key, value)
            
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def archive_object(self, object_id_or_uuid: Union[int, str]) -> DBRegistryObject:
        """Archive a registry object by setting its status to 'archived'."""
        db_obj = self._get_query(object_id_or_uuid).first()
        if not db_obj:
            raise ValueError(f"RegistryObject with identifier '{object_id_or_uuid}' not found")
            
        db_obj.status = "archived"
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
