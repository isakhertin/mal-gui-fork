from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6.QtGui import QUndoCommand
from ..connection_item import AssociationConnectionItem, EntrypointConnectionItem, GoalConnectionItem

if TYPE_CHECKING:
    from ..connection_item import IConnectionItem
    from ..model_scene import ModelScene

class DeleteConnectionCommand(QUndoCommand):
    def __init__(self, scene: ModelScene, item, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.connection: IConnectionItem = item

    def redo(self):
        """Perform delete connection"""
        if isinstance(self.connection, AssociationConnectionItem):
            self.scene.remove_association(self.connection)
        elif isinstance(self.connection, EntrypointConnectionItem):
            self.scene.remove_entrypoint(self.connection)
        elif isinstance(self.connection, GoalConnectionItem):
            self.scene.remove_goal(self.connection)
        else:
            raise ValueError("Unknown connection type")

    def undo(self):
        """Undo delete connection"""

        if isinstance(self.connection, AssociationConnectionItem):
            self.connection = self.scene.add_association_connection(
                self.connection.start_item,
                self.connection.end_item,
                self.connection.right_fieldname
            )
        elif isinstance(self.connection, EntrypointConnectionItem):
            self.connection = self.scene.add_entrypoint_connection(
                self.connection.attack_step_name,
                self.connection.attacker_item,
                self.connection.asset_item
            )
            step_full_name = (
                self.connection.asset_item.asset.name
                + ":"
                + self.connection.attack_step_name
            )
            if isinstance(self.connection.attacker_item.entry_points, set):
                self.connection.attacker_item.entry_points.add(step_full_name)
            elif step_full_name not in self.connection.attacker_item.entry_points:
                self.connection.attacker_item.entry_points.append(step_full_name)
        elif isinstance(self.connection, GoalConnectionItem):
            self.connection = self.scene.add_goal_connection(
                self.connection.attack_step_name,
                self.connection.attacker_item,
                self.connection.asset_item
            )
            step_full_name = (
                self.connection.asset_item.asset.name
                + ":"
                + self.connection.attack_step_name
            )
            if isinstance(self.connection.attacker_item.goals, set):
                self.connection.attacker_item.goals.add(step_full_name)
            elif step_full_name not in self.connection.attacker_item.goals:
                self.connection.attacker_item.goals.append(step_full_name)
        else:
            raise ValueError("Unknown connection type")
