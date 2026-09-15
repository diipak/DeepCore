from datetime import datetime, timezone
import json
import urllib.parse
from typing import Dict, Any, List
from sqlalchemy import func
from sqlalchemy.orm import Session

from deepcore2.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    KnowledgeSource as DBKnowledgeSource,
    SyncRun as DBSyncRun
)

class AwarenessService:
    """
    Awareness Service. COMPOSITION LAYER.
    Responsible for composing the human-centric AwarenessState model
    by query-aggregating focus, orientation, understanding, and continuation blocks.
    Can be extracted into a dedicated Awareness Runtime.
    """
    def __init__(self, db: Session, workspace_id: int):
        self.db = db
        self.workspace_id = workspace_id

    def get_awareness_state(self) -> Dict[str, Any]:
        focus_items = self._get_focus_intent()
        orientation_items = self._get_orientation()
        understanding_items = self._get_understanding()
        continuation_items = self._get_continuation(focus_items, understanding_items)

        # Overall summary statistics for header metrics
        memory_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.status == "active",
            DBRegistryObject.object_type.in_(["note", "video", "document", "event", "file"])
        ).count()

        concept_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged"
        ).count()

        relationship_count = self.db.query(DBRegistryRelationship).filter(
            DBRegistryRelationship.workspace_id == self.workspace_id
        ).count()

        return {
            "summary": {
                "memory_count": memory_count,
                "concept_count": concept_count,
                "relationship_count": relationship_count
            },
            "focus": focus_items,
            "orientation": orientation_items,
            "understanding": understanding_items,
            "continuation": continuation_items
        }

    def _get_focus_intent(self) -> List[Dict[str, Any]]:
        """
        Amendment 2 - Naming & design preserves Focus Intent abstraction.
        Extracts active focus items based on last accessed/modified records.
        """
        objs = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.status == "active",
            DBRegistryObject.object_type.in_(["note", "video", "document", "event"])
        ).order_by(
            DBRegistryObject.updated_at.desc()
        ).limit(3).all()

        focus_list = []
        for obj in objs:
            type_labels = {
                "note": "Markdown Note",
                "event": "Calendar Event",
                "video": "YouTube Capture",
                "document": "Indexed Document"
            }
            label = type_labels.get(obj.object_type, "Memory Object")
            
            delta = datetime.now() - obj.updated_at
            if delta.days > 0:
                time_str = f"{delta.days}d ago"
            elif delta.seconds > 3600:
                time_str = f"{delta.seconds // 3600}h ago"
            else:
                time_str = "just now"

            focus_list.append({
                "title": obj.title,
                "object_type": obj.object_type,
                "object_uuid": obj.uuid,
                "description": f"{label} • updated {time_str}",
                "last_accessed": time_str
            })
        return focus_list

    def _get_orientation(self) -> List[Dict[str, Any]]:
        """
        Amendment 1 - Explain what changed since the user was away.
        Groups updates by theme/source.
        """
        runs = self.db.query(DBSyncRun).order_by(
            DBSyncRun.started_at.desc()
        ).limit(3).all()

        changes = []
        for r in runs:
            delta = datetime.now() - r.started_at
            time_str = f"{delta.days}d ago" if delta.days > 0 else "recently"

            if r.objects_created > 0 or r.objects_updated > 0:
                changes.append({
                    "title": f"Synced {r.provider} library",
                    "change_type": "new_artifact",
                    "description": f"Discovered {r.objects_created} new and {r.objects_updated} updated records.",
                    "time_ago": time_str,
                    "object_uuid": None
                })

        recent_objs = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.status == "active"
        ).order_by(
            DBRegistryObject.created_at.desc()
        ).limit(3).all()

        for obj in recent_objs:
            if obj.location:
                delta = datetime.now() - obj.created_at
                time_str = f"{delta.days}d ago" if delta.days > 0 else "recently"
                changes.append({
                    "title": f"Indexed '{obj.title}'",
                    "change_type": "new_artifact",
                    "description": f"Ambiently absorbed {obj.object_type} content.",
                    "time_ago": time_str,
                    "object_uuid": obj.uuid
                })

        if not changes:
            changes.append({
                "title": "Quiet reflection state",
                "change_type": "updated_context",
                "description": "No new external updates detected. Your private memory web is stable.",
                "time_ago": "just now",
                "object_uuid": None
            })
            
        return changes[:5]

    def _get_understanding(self) -> List[Dict[str, Any]]:
        """
        Amendment 1 - Surface meaningful observations and emerging patterns.
        """
        observations = []

        # 1. Unapproved Concepts check
        unapproved_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.object_type == "concept",
            DBRegistryObject.status != "merged",
            func.json_extract(DBRegistryObject.metadata_json, '$.concept_status') == "candidate"
        ).count()

        if unapproved_count > 0:
            observations.append({
                "id": "unapproved_concepts_alert",
                "observation_type": "unapproved_concept",
                "title": f"{unapproved_count} New Concepts Discovered",
                "description": f"DeepCore extracted {unapproved_count} key terms from your files. Review and approve them to link them to your memory web.",
                "severity": "warning",
                "action_label": "Review Concepts",
                "action_route": "/platform"
            })

        # 2. Orphaned Memories check
        sub_from = self.db.query(DBRegistryRelationship.from_object_id)
        sub_to = self.db.query(DBRegistryRelationship.to_object_id)
        
        orphans = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.object_type == "note",
            DBRegistryObject.status == "active",
            ~DBRegistryObject.id.in_(sub_from),
            ~DBRegistryObject.id.in_(sub_to)
        ).limit(3).all()

        for o in orphans:
            safe_title = urllib.parse.quote(o.title)
            observations.append({
                "id": f"orphan_{o.uuid}",
                "observation_type": "orphan",
                "title": f"Orphaned Thread: '{o.title}'",
                "description": "This note has no semantic links or associations. Ask the Assistant to link it or add reference connections.",
                "severity": "info",
                "action_label": "Ask Assistant",
                "action_route": f"/assistant?prompt=Explain%20how%20to%20connect%20my%20note%20{safe_title}%20to%20other%20concepts"
            })

        # 3. Missing context check
        missing_count = self.db.query(DBRegistryObject).filter(
            DBRegistryObject.workspace_id == self.workspace_id,
            DBRegistryObject.status == "missing"
        ).count()

        if missing_count > 0:
            observations.append({
                "id": "missing_objects_alert",
                "observation_type": "deleted_context",
                "title": f"{missing_count} Missing Context Items",
                "description": f"We detected {missing_count} files were deleted or moved on disk. Review their memory history.",
                "severity": "info",
                "action_label": "Inspect Memories",
                "action_route": "/memories"
            })

        return observations

    def _get_continuation(self, focus_items: list, observations: list) -> List[Dict[str, Any]]:
        """
        Amendment 1 - Suggest next thinking step & pre-populate Assistant context.
        """
        steps = []

        if focus_items:
            primary_focus = focus_items[0]
            steps.append({
                "title": f"Elaborate on '{primary_focus['title']}'",
                "prompt": f"Synthesize what I should think about next regarding: '{primary_focus['title']}'. What are the adjacent concepts?",
                "action_label": "Start Thread"
            })
            steps.append({
                "title": f"Explain relationships of '{primary_focus['title']}'",
                "prompt": f"Show all active connections and references for '{primary_focus['title']}' in my memory library.",
                "action_label": "Map Links"
            })
        
        steps.append({
            "title": "Synthesize unlinked topics",
            "prompt": "Scan my private memory library for any disconnected or orphaned thoughts and suggest connections.",
            "action_label": "Analyze Web"
        })

        return steps[:3]
