# Copyright (c) 2022 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

import collections
from typing import OrderedDict, Optional

from PyQt6.QtCore import Qt, QTimer, QObject

import cura
from UM import i18nCatalog
from UM.Logger import Logger
from UM.Qt.ListModel import ListModel
from UM.Settings.ContainerRegistry import ContainerRegistry
from UM.Settings.Interfaces import ContainerInterface
from cura.Settings.IntentManager import IntentManager

catalog = i18nCatalog("cura")


class IntentSelectionModel(ListModel):

    NameRole = Qt.ItemDataRole.UserRole + 1
    IntentCategoryRole = Qt.ItemDataRole.UserRole + 2
    WeightRole = Qt.ItemDataRole.UserRole + 3
    DescriptionRole = Qt.ItemDataRole.UserRole + 4
    IconRole = Qt.ItemDataRole.UserRole + 5

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self.addRoleName(self.NameRole, "name")
        self.addRoleName(self.IntentCategoryRole, "intent_category")
        self.addRoleName(self.WeightRole, "weight")
        self.addRoleName(self.DescriptionRole, "description")
        self.addRoleName(self.IconRole, "icon")

        application = cura.CuraApplication.CuraApplication.getInstance()

        ContainerRegistry.getInstance().containerAdded.connect(self._onContainerChange)
        ContainerRegistry.getInstance().containerRemoved.connect(self._onContainerChange)
        machine_manager = cura.CuraApplication.CuraApplication.getInstance().getMachineManager()
        machine_manager.activeMaterialChanged.connect(self._update)
        machine_manager.activeVariantChanged.connect(self._update)
        machine_manager.extruderChanged.connect(self._update)

        extruder_manager = application.getExtruderManager()
        extruder_manager.extrudersChanged.connect(self._update)

        self._update_timer: QTimer = QTimer()
        self._update_timer.setInterval(100)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update)

        self._onChange()

    @staticmethod
    def _getDefaultProfileInformation() -> OrderedDict[str, dict]:
        """ Default information user-visible string. Ordered by weight. """
        default_profile_information = collections.OrderedDict()
        default_profile_information["default"] = {
            "name": catalog.i18nc("@label", "Default"),
            "icon": "GearCheck"
        }
        default_profile_information["visual"] = {
            "name": catalog.i18nc("@label", "Visual"),
            "description": catalog.i18nc("@text", "The visual profile is designed to print visual prototypes and models with the intent of high visual and surface quality."),
            "icon" : "Visual"
        }
        default_profile_information["engineering"] = {
            "name": catalog.i18nc("@label", "Engineering"),
            "description": catalog.i18nc("@text", "The engineering profile is designed to print functional prototypes and end-use parts with the intent of better accuracy and for closer tolerances."),
            "icon": "Nut"
        }
        default_profile_information["quick"] = {
            "name": catalog.i18nc("@label", "Draft"),
            "description": catalog.i18nc("@text", "The draft profile is designed to print initial prototypes and concept validation with the intent of significant print time reduction."),
            "icon": "SpeedOMeter"
        }
        default_profile_information["annealing"] = {
            "name": catalog.i18nc("@label", "Annealing"),
            "description": catalog.i18nc("@text",
                                         "The annealing profile requires post-processing in an oven after the print is finished. This profile retains the dimensional accuracy of the printed part after annealing and improves strength, stiffness, and thermal resistance."),
            "icon": "Anneal"
        }
        return default_profile_information

    def _onContainerChange(self, container: ContainerInterface) -> None:
        """Updates the list of intents if an intent profile was added or removed."""

        if container.getMetaDataEntry("type") == "intent":
            self._update()

    def _onChange(self) -> None:
        self._update_timer.start()

    def _update(self) -> None:
        Logger.log("d", "Updating {model_class_name}.".format(model_class_name = self.__class__.__name__))

        global_stack = cura.CuraApplication.CuraApplication.getInstance().getGlobalContainerStack()
        if global_stack is None:
            self.setItems([])
            Logger.log("d", "No active GlobalStack, set quality profile model as empty.")
            return

        # Check for material compatibility
        if not cura.CuraApplication.CuraApplication.getInstance().getMachineManager().activeMaterialsCompatible():
            Logger.log("d", "No active material compatibility, set quality profile model as empty.")
            self.setItems([])
            return

        default_profile_info = self._getDefaultProfileInformation()

        available_categories = IntentManager.getInstance().currentAvailableIntentCategories()
        result = []
        for i, category in enumerate(available_categories):
            profile_info = default_profile_info.get(category, {})

            try:
                weight = list(default_profile_info.keys()).index(category)
            except ValueError:
                weight = len(available_categories) + i

            result.append({
                "name": profile_info.get("name", category.title()),
                "description": profile_info.get("description", None),
                "icon" : profile_info.get("icon", ""),
                "intent_category": category,
                "weight": weight,
            })

        result.sort(key=lambda k: k["weight"])

        self.setItems(result)


