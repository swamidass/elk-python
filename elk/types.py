"""Type definitions for ELK server input and output.

These types are based on the ELK server JSON format specification from:
https://raw.githubusercontent.com/TypeFox/elk-server/refs/heads/main/README.md
"""

from typing import Dict, List, Union

from pydantic import BaseModel, Field


class Point(BaseModel):
    """A point in 2D space."""

    x: float
    y: float


class Dimension(BaseModel):
    """Dimensions of a shape."""

    width: float
    height: float


class ShapeLayoutElement(BaseModel):
    """Layout information for a shape element."""

    position: Point
    size: Dimension


class EdgeLayoutElement(BaseModel):
    """Layout information for an edge element."""

    route: List[Point]


LayoutElement = Union[ShapeLayoutElement, EdgeLayoutElement]


class LayoutData(BaseModel):
    """Layout data mapping element IDs to their layout information."""

    root: Dict[str, LayoutElement] = Field(
        description="Mapping of element IDs to layout data",
    )


class ElkError(BaseModel):
    """Error response from the ELK server."""

    message: str
    name: str
    stack: str


# Input types for the ELK graph format
# Based on https://www.eclipse.org/elk/documentation/tooldevelopers/graphdatastructure/jsonformat.html


class ElkProperties(BaseModel):
    """Properties that can be set on any graph element."""

    algorithm: str | None = Field(None, description="Layout algorithm to use")
    # Add more properties as needed


class ElkPort(BaseModel):
    """A port on a node."""

    id: str
    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    properties: ElkProperties | None = None


class ElkLabel(BaseModel):
    """A label that can be attached to any graph element."""

    text: str
    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None


class ElkEdge(BaseModel):
    """An edge connecting two nodes."""

    id: str
    sources: List[str]
    targets: List[str]
    properties: ElkProperties | None = None
    labels: List[ElkLabel] | None = None


class ElkNode(BaseModel):
    """A node in the graph."""

    id: str
    width: float | None = None
    height: float | None = None
    x: float | None = None
    y: float | None = None
    properties: ElkProperties | None = None
    labels: List[ElkLabel] | None = None
    ports: List[ElkPort] | None = None
    children: List["ElkNode"] | None = None
    edges: List[ElkEdge] | None = None


class ElkGraph(BaseModel):
    """The root graph object."""

    id: str
    properties: ElkProperties | None = None
    children: List[ElkNode] | None = None
    edges: List[ElkEdge] | None = None
