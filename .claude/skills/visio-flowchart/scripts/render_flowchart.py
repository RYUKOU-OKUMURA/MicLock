#!/usr/bin/env python3
"""
Visio-style Flowchart Renderer
Renders Mermaid flowchart (graph TB) notation as PNG images with Visio-like styling.
"""

import re
import argparse
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Error: PIL/Pillow is required. Install with: pip install Pillow")
    exit(1)

# Design Constants
BG_COLOR = "#F7F7F7"
LANE_BG_COLOR = "#FFFFFF"
LANE_BORDER_COLOR = "#CCCCCC"
HEADER_BG_COLOR = "#4A90E2"
HEADER_TEXT_COLOR = "#FFFFFF"
BOX_BORDER_COLOR = "#4A90E2"
BOX_BG_COLOR = "#FFFFFF"
ARROW_COLOR = "#555555"
TEXT_COLOR = "#333333"

# Layer Colors from requirements
PRESENTATION_COLOR = "#e1f5ff"
APPLICATION_COLOR = "#fff4e1"
DOMAIN_COLOR = "#f0e1ff"
INFRASTRUCTURE_COLOR = "#e8f5e9"
STATE_COLOR = "#ffebee"

# Layout constants
SCALE = 2
FONT_SIZE_HEADER = 14
FONT_SIZE_BOX = 12
FONT_SIZE_LABEL = 11
BOX_WIDTH = 180
BOX_HEIGHT = 60
BOX_MARGIN = 20
SUBGRAPH_MARGIN = 30
ARROW_SPACING = 40


class LayerType(Enum):
    PRESENTATION = "presentation"
    APPLICATION = "application"
    DOMAIN = "domain"
    INFRASTRUCTURE = "infrastructure"
    STATE = "state"
    OTHER = "other"


@dataclass
class Node:
    id: str
    label: str
    layer: Optional[str] = None
    layer_type: LayerType = LayerType.OTHER


@dataclass
class Edge:
    from_id: str
    to_id: str
    label: Optional[str] = None


@dataclass
class Subgraph:
    id: str
    label: str
    layer_type: LayerType = LayerType.OTHER
    nodes: List[Node] = None
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []


def detect_layer_type(label: str) -> LayerType:
    """Detect layer type from label text."""
    label_lower = label.lower()
    if "presentation" in label_lower or "swiftui" in label_lower:
        return LayerType.PRESENTATION
    elif "application" in label_lower:
        return LayerType.APPLICATION
    elif "domain" in label_lower:
        return LayerType.DOMAIN
    elif "infrastructure" in label_lower:
        return LayerType.INFRASTRUCTURE
    elif "state" in label_lower or "状態" in label_lower:
        return LayerType.STATE
    return LayerType.OTHER


def get_layer_color(layer_type: LayerType) -> str:
    """Get background color for layer type."""
    colors = {
        LayerType.PRESENTATION: PRESENTATION_COLOR,
        LayerType.APPLICATION: APPLICATION_COLOR,
        LayerType.DOMAIN: DOMAIN_COLOR,
        LayerType.INFRASTRUCTURE: INFRASTRUCTURE_COLOR,
        LayerType.STATE: STATE_COLOR,
        LayerType.OTHER: BOX_BG_COLOR,
    }
    return colors.get(layer_type, BOX_BG_COLOR)


def parse_mermaid(content: str) -> Tuple[List[Subgraph], List[Node], List[Edge]]:
    """Parse Mermaid graph TB notation."""
    lines = content.strip().split('\n')

    subgraphs: Dict[str, Subgraph] = {}
    nodes: Dict[str, Node] = {}
    edges: List[Edge] = []

    current_subgraph = None
    in_subgraph = False

    for line in lines:
        line = line.strip()
        if not line or line.startswith('%%'):
            continue

        # Subgraph start
        if line.startswith('subgraph'):
            match = re.match(r'subgraph\s+(\[?["\']?([^"\"\]]+)["\']?\]?)', line)
            if match:
                sg_id = match.group(1).strip('[]')
                sg_label = match.group(2) if len(match.groups()) > 1 else sg_id
                layer_type = detect_layer_type(sg_label)
                current_subgraph = Subgraph(id=sg_id, label=sg_label, layer_type=layer_type)
                subgraphs[sg_id] = current_subgraph
                in_subgraph = True
            continue

        # Subgraph end
        if line == 'end':
            in_subgraph = False
            current_subgraph = None
            continue

        # Node definition
        node_match = re.match(r'(\w+)\[([^\]]+)\]', line)
        if node_match:
            node_id = node_match.group(1)
            # Handle HTML-like labels (e.g., <br/>)
            label = node_match.group(2).replace('<br/>', '\n').replace('<br>', '\n')
            label = re.sub(r'<[^>]+>', '', label)  # Remove other HTML tags

            node = Node(id=node_id, label=label)
            if current_subgraph:
                node.layer = current_subgraph.id
                node.layer_type = current_subgraph.layer_type
                current_subgraph.nodes.append(node)
            nodes[node_id] = node
            continue

        # Edge definition with optional label
        edge_match = re.match(r'(\w+)\s*-->\s*(\|[^|]+\|)?\s*(\w+)', line)
        if edge_match:
            from_id = edge_match.group(1)
            label_text = edge_match.group(2)
            to_id = edge_match.group(3)

            if label_text:
                label_text = label_text.strip('|')

            if from_id in nodes and to_id in nodes:
                edges.append(Edge(from_id=from_id, to_id=to_id, label=label_text))
            continue

        # Simple edge (no label)
        simple_edge = re.match(r'(\w+)\s*-->\s*(\w+)', line)
        if simple_edge:
            from_id = simple_edge.group(1)
            to_id = simple_edge.group(2)
            if from_id in nodes and to_id in nodes:
                edges.append(Edge(from_id=from_id, to_id=to_id))

    # Style directive parsing (for node styles)
    for line in lines:
        style_match = re.match(r'style\s+(\w+)\s+fill:(#[\da-fA-F]+)', line)
        if style_match:
            node_id = style_match.group(1)
            fill_color = style_match.group(2)
            if node_id in subgraphs:
                # For subgraphs, we could apply custom color if needed
                pass
            elif node_id in nodes:
                # Could apply node-specific colors here
                pass

    return list(subgraphs.values()), list(nodes.values()), edges


def calculate_layout(subgraphs: List[Subgraph], nodes: List[Node], edges: List[Edge]) -> Tuple[int, int]:
    """Calculate layout positions for all elements."""
    x_offset = SUBGRAPH_MARGIN
    y_offset = SUBGRAPH_MARGIN

    # Position subgraphs horizontally
    for sg in subgraphs:
        # Calculate subgraph dimensions based on nodes
        if sg.nodes:
            sg.height = len(sg.nodes) * (BOX_HEIGHT + BOX_MARGIN) + BOX_MARGIN * 2 + 30
            sg.width = BOX_WIDTH + BOX_MARGIN * 2
        else:
            sg.height = 100
            sg.width = 200

        sg.x = x_offset
        sg.y = y_offset
        x_offset += sg.width + SUBGRAPH_MARGIN

    # Position nodes within subgraphs
    for sg in subgraphs:
        node_y = sg.y + 40  # Space for header
        for node in sg.nodes:
            node.x = sg.x + BOX_MARGIN
            node.y = node_y
            node_y += BOX_HEIGHT + BOX_MARGIN

    # Position nodes not in any subgraph
    orphan_nodes = [n for n in nodes if not any(n.id in [node.id for node in sg.nodes] for sg in subgraphs)]
    if orphan_nodes:
        orphan_x = x_offset
        orphan_y = y_offset
        for node in orphan_nodes:
            node.x = orphan_x
            node.y = orphan_y
            orphan_y += BOX_HEIGHT + BOX_MARGIN

    # Calculate total canvas size
    total_width = max(
        x_offset,
        max((n.x + BOX_WIDTH for n in nodes), default=x_offset)
    ) + SUBGRAPH_MARGIN

    total_height = max(
        max((sg.y + sg.height for sg in subgraphs), default=0),
        max((n.y + BOX_HEIGHT for n in nodes), default=0)
    ) + SUBGRAPH_MARGIN

    return total_width, total_height


def draw_arrow(draw: ImageDraw.Draw, from_x: int, from_y: int, to_x: int, to_y: int, label: Optional[str] = None):
    """Draw an arrow between two points."""
    color = ARROW_COLOR

    # Calculate arrow head
    angle = 0.5  # Arrow head angle in radians
    head_length = 10

    dx = to_x - from_x
    dy = to_y - from_y
    length = (dx * dx + dy * dy) ** 0.5

    if length == 0:
        return

    # Unit vector
    ux = dx / length
    uy = dy / length

    # Adjust end point to box edge
    if from_x < to_x:  # Left to right
        end_x = to_x - 5
        end_y = to_y
        start_x = from_x + BOX_WIDTH
        start_y = from_y + BOX_HEIGHT // 2
    elif from_x > to_x:  # Right to left
        end_x = to_x + BOX_WIDTH
        end_y = to_y
        start_x = from_x - 5
        start_y = from_y + BOX_HEIGHT // 2
    else:  # Vertical
        end_x = to_x + BOX_WIDTH // 2
        end_y = to_y - 5
        start_x = from_x + BOX_WIDTH // 2
        start_y = from_y + BOX_HEIGHT

    # Draw line
    draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=2)

    # Draw arrow head
    ax1 = end_x - head_length * ux * 0.7 - head_length * uy * 0.5
    ay1 = end_y - head_length * uy * 0.7 + head_length * ux * 0.5
    ax2 = end_x - head_length * ux * 0.7 + head_length * uy * 0.5
    ay2 = end_y - head_length * uy * 0.7 - head_length * ux * 0.5

    draw.polygon([(end_x, end_y), (ax1, ay1), (ax2, ay2)], fill=color)

    # Draw label
    if label:
        mid_x = (start_x + end_x) // 2
        mid_y = (start_y + end_y) // 2

        # Draw label background
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(FONT_SIZE_LABEL * SCALE))
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), label, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        padding = 4
        draw.rectangle(
            [(mid_x - text_width // 2 - padding, mid_y - text_height // 2 - padding),
             (mid_x + text_width // 2 + padding, mid_y + text_height // 2 + padding)],
            fill=BG_COLOR
        )
        draw.text((mid_x - text_width // 2, mid_y - text_height // 2), label, fill=TEXT_COLOR, font=font)


def render_flowchart(content: str, title: str = "Flowchart") -> Image.Image:
    """Render Mermaid flowchart to PIL Image."""
    subgraphs, nodes, edges = parse_mermaid(content)
    width, height = calculate_layout(subgraphs, nodes, edges)

    # Scale dimensions
    width = int(width * SCALE)
    height = int(height * SCALE)

    # Create image
    img = Image.new('RGB', (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Try to load fonts
    try:
        header_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(FONT_SIZE_HEADER * SCALE))
        box_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(FONT_SIZE_BOX * SCALE))
    except:
        try:
            header_font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(FONT_SIZE_HEADER * SCALE))
            box_font = ImageFont.truetype("DejaVuSans.ttf", int(FONT_SIZE_BOX * SCALE))
        except:
            header_font = ImageFont.load_default()
            box_font = ImageFont.load_default()

    # Draw title
    if title:
        title_bbox = draw.textbbox((0, 0), title, font=header_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 10), title, fill=TEXT_COLOR, font=header_font)
        title_height = title_bbox[3] - title_bbox[1] + 20
    else:
        title_height = 10

    # Draw subgraphs
    for sg in subgraphs:
        x = int(sg.x * SCALE)
        y = int(sg.y * SCALE) + title_height
        w = int(sg.width * SCALE)
        h = int(sg.height * SCALE)

        bg_color = get_layer_color(sg.layer_type)

        # Draw subgraph background
        draw.rectangle([x, y, x + w, y + h], fill=bg_color, outline=LANE_BORDER_COLOR, width=2)

        # Draw header
        header_height = int(30 * SCALE)
        draw.rectangle([x, y, x + w, y + header_height], fill=HEADER_BG_COLOR)

        # Draw header text
        header_bbox = draw.textbbox((0, 0), sg.label, font=header_font)
        header_text_width = header_bbox[2] - header_bbox[0]
        draw.text((x + (w - header_text_width) // 2, y + 5), sg.label, fill=HEADER_TEXT_COLOR, font=header_font)

    # Draw nodes
    for node in nodes:
        if node.layer:
            continue  # Skip nodes in subgraphs (they'll be drawn within)
        x = int(node.x * SCALE)
        y = int(node.y * SCALE) + title_height
        w = int(BOX_WIDTH * SCALE)
        h = int(BOX_HEIGHT * SCALE)

        # Draw rounded rectangle
        draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=BOX_BG_COLOR, outline=BOX_BORDER_COLOR, width=2)

        # Draw text
        lines = node.label.split('\n')
        text_y = y + (h - len(lines) * int(FONT_SIZE_BOX * SCALE)) // 2

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=box_font)
            text_width = bbox[2] - bbox[0]
            draw.text((x + (w - text_width) // 2, text_y), line, fill=TEXT_COLOR, font=box_font)
            text_y += int(FONT_SIZE_BOX * SCALE) + 2

    # Draw nodes within subgraphs
    for sg in subgraphs:
        sg_y = int(sg.y * SCALE) + title_height
        for node in sg.nodes:
            x = int(node.x * SCALE)
            y = int(node.y * SCALE) + title_height
            w = int(BOX_WIDTH * SCALE)
            h = int(BOX_HEIGHT * SCALE)

            # Draw rounded rectangle
            draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=BOX_BG_COLOR, outline=BOX_BORDER_COLOR, width=2)

            # Draw text
            lines = node.label.split('\n')
            text_y = y + (h - len(lines) * int(FONT_SIZE_BOX * SCALE)) // 2

            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=box_font)
                text_width = bbox[2] - bbox[0]
                draw.text((x + (w - text_width) // 2, text_y), line, fill=TEXT_COLOR, font=box_font)
                text_y += int(FONT_SIZE_BOX * SCALE) + 2

    # Draw edges
    for edge in edges:
        from_node = next((n for n in nodes if n.id == edge.from_id), None)
        to_node = next((n for n in nodes if n.id == edge.to_id), None)

        if from_node and to_node:
            draw_arrow(
                draw,
                int(from_node.x * SCALE),
                int(from_node.y * SCALE) + title_height,
                int(to_node.x * SCALE),
                int(to_node.y * SCALE) + title_height,
                edge.label
            )

    return img


def main():
    parser = argparse.ArgumentParser(description='Render Mermaid flowchart as PNG')
    parser.add_argument('input', help='Input Mermaid file (.mmd)')
    parser.add_argument('-o', '--output', default='flowchart.png', help='Output PNG file')
    parser.add_argument('-t', '--title', default='Flowchart', help='Chart title')

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as f:
        content = f.read()

    img = render_flowchart(content, args.title)
    img.save(args.output, 'PNG')
    print(f"Flowchart saved to {args.output}")


if __name__ == '__main__':
    main()
