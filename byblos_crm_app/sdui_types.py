"""SDUI type definitions for Byblos CRM (Python/Streamlit)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SDUIAction:
    type: str  # 'navigate' | 'submit' | 'open_modal'
    target: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"type": self.type}
        if self.target:
            d["target"] = self.target
        return d


@dataclass
class SDUIColumn:
    key: str
    label: str
    type: str = "text"  # 'text' | 'badge' | 'currency' | 'avatar_text'

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "type": self.type}


@dataclass
class SDUIComponent:
    type: str
    id: Optional[str] = None
    props: Optional[dict] = None
    children: list[SDUIComponent] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type}
        if self.id:
            d["id"] = self.id
        if self.props:
            d["props"] = self.props
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


@dataclass
class SDUIScreen:
    id: str
    title: str
    root: SDUIComponent

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "root": self.root.to_dict()}


@dataclass
class SDUINavItem:
    id: str
    label: str
    icon: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "icon": self.icon}


@dataclass
class SDUIConfig:
    nav: list[SDUINavItem]
    screens: list[SDUIScreen]
    defaultScreenId: str

    def to_dict(self) -> dict:
        return {
            "nav": [n.to_dict() for n in self.nav],
            "screens": [s.to_dict() for s in self.screens],
            "defaultScreenId": self.defaultScreenId,
        }
