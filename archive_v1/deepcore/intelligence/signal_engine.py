import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from deepcore.storage.sqlite.models import (
    RegistryObject as DBRegistryObject,
    RegistryRelationship as DBRegistryRelationship,
    RegistrySignal as DBRegistrySignal,
    ObjectActivityLog as DBObjectActivityLog,
    generate_uuid,
    get_utc_now
)
from deepcore.core.objects.schemas import SignalType
from deepcore.core.providers.base import SyncResult

class SignalPolicy:
    """
    Centralized configuration holding all thresholds for deterministic signal detection.
    """
    def __init__(
        self,
        recent_activity_days: int = 7,
        dormancy_days: int = 30,
        frequent_activity_threshold: int = 3,
        high_reference_threshold: int = 3
    ):
        self.recent_activity_days = recent_activity_days
        self.dormancy_days = dormancy_days
        self.frequent_activity_threshold = frequent_activity_threshold
        self.high_reference_threshold = high_reference_threshold


DEFAULT_SIGNAL_POLICY = SignalPolicy()


class SignalEngine:
    """
    Deterministic Signal Engine evaluating canonical registry objects and relationships
    to produce explainable temporal observations.
    """
    def __init__(self, db: Session, workspace_id: Optional[int] = None, policy: SignalPolicy = DEFAULT_SIGNAL_POLICY):
        self.db = db
        if workspace_id is None:
            from deepcore.storage.sqlite.models import Workspace
            personal = db.query(Workspace).filter(Workspace.name == "Personal Workspace").first()
            if not personal:
                personal = Workspace(name="Personal Workspace")
                db.add(personal)
                db.commit()
                db.refresh(personal)
            self.workspace_id = personal.id
        else:
            self.workspace_id = workspace_id
        self.policy = policy

    def process_sync_result(self, sync_result: SyncResult, pipeline_result: Optional[Any] = None) -> int:
        """
        Evaluate and update temporal signals for objects affected by the sync run.
        Updates the ObjectActivityLog first, then computes active signals.
        """
        # 1. Log activity for created and updated objects
        for obj in sync_result.created:
            log_entry = DBObjectActivityLog(
                object_id=obj.id,
                workspace_id=self.workspace_id,
                action="created",
                timestamp=get_utc_now()
            )
            self.db.add(log_entry)
        
        for obj in sync_result.updated:
            log_entry = DBObjectActivityLog(
                object_id=obj.id,
                workspace_id=self.workspace_id,
                action="updated",
                timestamp=get_utc_now()
            )
            self.db.add(log_entry)
            
        self.db.commit()

        # 2. Process signals for all created/updated objects
        affected_objects = sync_result.created + sync_result.updated
        processed_count = 0
        
        for obj in affected_objects:
            if obj.object_type == "note":
                self.evaluate_object_signals(obj, pipeline_result)
                processed_count += 1

        # 3. Clean up signals for missing or inactive objects
        missing_or_inactive_ids = [obj.id for obj in sync_result.missing]
        
        # Query any objects that became inactive in this run
        all_affected_ids = [obj.id for obj in affected_objects]
        if all_affected_ids:
            inactive_objs = self.db.query(DBRegistryObject).filter(
                DBRegistryObject.workspace_id == self.workspace_id,
                DBRegistryObject.id.in_(all_affected_ids),
                DBRegistryObject.status != "active"
            ).all()
            missing_or_inactive_ids.extend([obj.id for obj in inactive_objs])

        if missing_or_inactive_ids:
            self.db.query(DBRegistrySignal).filter(
                DBRegistrySignal.workspace_id == self.workspace_id,
                DBRegistrySignal.target_object_id.in_(missing_or_inactive_ids)
            ).delete(synchronize_session=False)
            self.db.commit()

        return processed_count

    def evaluate_object_signals(self, obj: DBRegistryObject, pipeline_result: Optional[Any] = None) -> None:
        """
        Evaluate all deterministic signals for a single object based on policy thresholds,
        updating the database using semantic lifecycle logic.
        """
        if obj.status != "active":
            # Inactive objects should have no active signals
            self.db.query(DBRegistrySignal).filter(
                DBRegistrySignal.workspace_id == self.workspace_id,
                DBRegistrySignal.target_object_id == obj.id
            ).delete(synchronize_session=False)
            self.db.commit()
            return

        now = get_utc_now()
        now_naive = now.replace(tzinfo=None)
        obj_updated_naive = obj.updated_at.replace(tzinfo=None) if obj.updated_at else now_naive
        age_delta = now_naive - obj_updated_naive

        # Gather computed signals that SHOULD exist
        computed_signals: List[Dict[str, Any]] = []

        # Rule A: RECENT_ACTIVITY
        if age_delta <= timedelta(days=self.policy.recent_activity_days):
            hours_ago = age_delta.total_seconds() / 3600.0
            computed_signals.append({
                "signal_type": SignalType.RECENT_ACTIVITY.value,
                "value": "recent",
                "confidence": 1.0,
                "evidence": {
                    "type": "temporal_recency",
                    "detail": f"Note was updated recently ({hours_ago:.1f} hours ago, threshold is within {self.policy.recent_activity_days} days)",
                    "measured_value": f"{hours_ago:.1f} hours",
                    "threshold": f"{self.policy.recent_activity_days} days",
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Rule B: DORMANT
        if age_delta > timedelta(days=self.policy.dormancy_days):
            days_ago = age_delta.days
            computed_signals.append({
                "signal_type": SignalType.DORMANT.value,
                "value": "dormant",
                "confidence": 1.0,
                "evidence": {
                    "type": "temporal_dormancy",
                    "detail": f"Note has not been modified for {days_ago} days (dormancy threshold is {self.policy.dormancy_days} days)",
                    "measured_value": f"{days_ago} days",
                    "threshold": f"{self.policy.dormancy_days} days",
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Rule C: FREQUENT_ACTIVITY
        mod_count = self.db.query(DBObjectActivityLog).filter(
            DBObjectActivityLog.workspace_id == self.workspace_id,
            DBObjectActivityLog.object_id == obj.id
        ).count()
        if mod_count >= self.policy.frequent_activity_threshold:
            computed_signals.append({
                "signal_type": SignalType.FREQUENT_ACTIVITY.value,
                "value": "frequent",
                "confidence": 1.0,
                "evidence": {
                    "type": "temporal_frequency",
                    "detail": f"Note has been modified {mod_count} times (frequent activity threshold is {self.policy.frequent_activity_threshold} times)",
                    "measured_value": mod_count,
                    "threshold": self.policy.frequent_activity_threshold,
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Query incoming relationships for reference signals
        incoming_rels = self.db.query(DBRegistryRelationship).filter(
            DBRegistryRelationship.workspace_id == self.workspace_id,
            DBRegistryRelationship.to_object_id == obj.id
        ).all()
        outgoing_rels = self.db.query(DBRegistryRelationship).filter(
            DBRegistryRelationship.workspace_id == self.workspace_id,
            DBRegistryRelationship.from_object_id == obj.id
        ).all()
        
        total_rels_count = len(incoming_rels) + len(outgoing_rels)

        # Rule D: HIGH_REFERENCE_COUNT
        incoming_count = len(incoming_rels)
        if incoming_count >= self.policy.high_reference_threshold:
            computed_signals.append({
                "signal_type": SignalType.HIGH_REFERENCE_COUNT.value,
                "value": "highly_referenced",
                "confidence": 1.0,
                "evidence": {
                    "type": "reference_count",
                    "detail": f"Note has {incoming_count} incoming references (high reference threshold is {self.policy.high_reference_threshold})",
                    "measured_value": incoming_count,
                    "threshold": self.policy.high_reference_threshold,
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Rule E: ORPHAN_NOTE
        if total_rels_count == 0:
            computed_signals.append({
                "signal_type": SignalType.ORPHAN_NOTE.value,
                "value": "orphan",
                "confidence": 1.0,
                "evidence": {
                    "type": "isolation",
                    "detail": "Note has 0 total relationships",
                    "measured_value": 0,
                    "threshold": 0,
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Rule F: BROKEN_REFERENCE
        # Retrieve unresolved links from transient pipeline context
        unresolved_links = []
        if pipeline_result is not None:
            unresolved_links = pipeline_result.context.get(f"unresolved_links:{obj.id}", [])

        for link in unresolved_links:
            computed_signals.append({
                "signal_type": SignalType.BROKEN_REFERENCE.value,
                "value": link,  # store the target link as the value to differentiate multiple broken links
                "confidence": 1.0,
                "evidence": {
                    "type": "broken_link",
                    "detail": f"Link to '{link}' is broken because the target does not exist or is inactive",
                    "target_title": link,
                    "producing_stage": "temporal_signal_engine"
                }
            })

        # Fetch existing signals for this object
        existing_signals = self.db.query(DBRegistrySignal).filter(
            DBRegistrySignal.workspace_id == self.workspace_id,
            DBRegistrySignal.target_object_id == obj.id
        ).all()

        # Build maps for matching existing vs computed
        # Single-instance signals match by signal_type.
        # Multi-instance signals (BROKEN_REFERENCE) match by (signal_type, value).
        existing_map: Dict[Any, DBRegistrySignal] = {}
        for sig in existing_signals:
            if sig.signal_type == SignalType.BROKEN_REFERENCE.value:
                existing_map[(sig.signal_type, sig.value)] = sig
            else:
                existing_map[sig.signal_type] = sig

        computed_keys = set()
        for computed in computed_signals:
            sig_type = computed["signal_type"]
            val = computed["value"]
            key = (sig_type, val) if sig_type == SignalType.BROKEN_REFERENCE.value else sig_type
            computed_keys.add(key)

            if key in existing_map:
                # Update existing signal (preserves ID, UUID, created_at)
                existing_sig = existing_map[key]
                existing_sig.value = val
                existing_sig.confidence = computed["confidence"]
                existing_sig.evidence_json = json.dumps(computed["evidence"])
                existing_sig.updated_at = get_utc_now()
                self.db.add(existing_sig)
            else:
                # Create new signal
                new_sig = DBRegistrySignal(
                    uuid=generate_uuid(),
                    workspace_id=self.workspace_id,
                    signal_type=sig_type,
                    target_object_id=obj.id,
                    value=val,
                    confidence=computed["confidence"],
                    generated_by="temporal_signal_engine",
                    evidence_json=json.dumps(computed["evidence"]),
                    created_at=get_utc_now(),
                    updated_at=get_utc_now()
                )
                self.db.add(new_sig)

        # Delete any existing signals that should no longer exist
        for key, existing_sig in existing_map.items():
            if key not in computed_keys:
                self.db.delete(existing_sig)

        self.db.commit()
