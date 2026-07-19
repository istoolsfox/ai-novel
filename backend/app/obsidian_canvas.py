from typing import Any


def story_canvas(ctx: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    canvas_nodes, canvas_edges, node_ids = [], [], {}
    for thread_index, thread_key in enumerate(ctx["threads"]):
        canvas_nodes.append({"id": f"thread-{thread_index}", "type": "file", "file": ctx["thread_paths"][thread_key], "x": thread_index * 520, "y": 0, "width": 360, "height": 220})
        rows = [row for row in ctx["nodes"].values() if str(row.get("thread_key") or "") == thread_key]
        rows.sort(key=lambda row: (int(row.get("planned_chapter") or 0), str(row.get("node_key") or "")))
        for node_index, row in enumerate(rows):
            key = str(row.get("node_key") or "")
            node_id = f"node-{thread_index}-{node_index}"
            node_ids[key] = node_id
            canvas_nodes.append({"id": node_id, "type": "file", "file": ctx["node_paths"][key], "x": thread_index * 520, "y": 300 + node_index * 300, "width": 360, "height": 220})
    for index, edge in enumerate(edges):
        source, target = node_ids.get(str(edge.get("source_node_key") or "")), node_ids.get(str(edge.get("target_node_key") or ""))
        if source and target:
            canvas_edges.append({"id": f"edge-{index}", "fromNode": source, "fromSide": "bottom", "toNode": target, "toSide": "top", "label": str(edge.get("relation_type") or "continues")})
    return {"nodes": canvas_nodes, "edges": canvas_edges}


def worldline_canvas(data: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    canvas_nodes, canvas_edges, chapter_ids, thread_ids = [], [], {}, {}
    for index, chapter in enumerate(data["chapters"]):
        number = int(chapter.get("chapter_number") or 0)
        node_id = f"chapter-{number}"
        chapter_ids[number] = node_id
        canvas_nodes.append({"id": node_id, "type": "file", "file": ctx["chapter_paths"][number], "x": index * 440, "y": 0, "width": 340, "height": 220})
        if index:
            previous = int(data["chapters"][index - 1].get("chapter_number") or 0)
            canvas_edges.append({"id": f"chapter-flow-{previous}-{number}", "fromNode": chapter_ids[previous], "fromSide": "right", "toNode": node_id, "toSide": "left", "label": "下一章"})
    for index, (thread_key, path) in enumerate(ctx["thread_paths"].items()):
        node_id = f"thread-overview-{index}"
        thread_ids[thread_key] = node_id
        canvas_nodes.append({"id": node_id, "type": "file", "file": path, "x": index * 440, "y": 500, "width": 340, "height": 220})
    edge_index = 0
    for chapter_number, rows in ctx["progress_by_chapter"].items():
        for row in rows:
            thread_key = str(row.get("thread_key") or "")
            if chapter_number in chapter_ids and thread_key in thread_ids:
                canvas_edges.append({"id": f"progress-{edge_index}", "fromNode": chapter_ids[chapter_number], "fromSide": "bottom", "toNode": thread_ids[thread_key], "toSide": "top", "label": str(row.get("progress_type") or "推进")})
                edge_index += 1
    return {"nodes": canvas_nodes, "edges": canvas_edges}
