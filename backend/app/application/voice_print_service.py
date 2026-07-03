"""Application: character voice print service.

Manages the character voice print lifecycle:
  1. Injection: inject voice_print into generation context for draft
  2. Check: archaeology checks dialogue against voice_print for consistency
  3. Update: when archaeology discovers new speech traits, write back to voice_print

Voice print structure (stored in characters.voice_print JSON column):
{
    "speech_habits": ["short sentences", "rarely uses exclamation"],
    "vocabulary_tendency": ["formal", "uses classical terms"],
    "avoid_words": ["would never say 'baby'"],
    "emotional_tells": ["repeats others' words when nervous", "looks away when lying"],
    "sample_dialogues": [
        {"context": "when questioned", "line": "You're right.", "subtext": "disagrees but won't argue"}
    ]
}
"""
import json
from typing import Any

from ..infrastructure.database import connect, row_to_dict, rows_to_dicts


def get_voice_print(project_id: str, character_id: str) -> dict[str, Any]:
    """Get a character's voice print. Returns empty dict if not set."""
    with connect() as conn:
        char = row_to_dict(
            conn.execute(
                "SELECT * FROM characters WHERE id = ? AND project_id = ?",
                (character_id, project_id),
            ).fetchone()
        )
    if not char:
        return {}
    vp = char.get("voice_print", "{}")
    if isinstance(vp, str):
        try:
            return json.loads(vp)
        except json.JSONDecodeError:
            return {}
    return vp if isinstance(vp, dict) else {}


def get_all_voice_prints(project_id: str) -> dict[str, dict[str, Any]]:
    """Get all characters' voice prints for a project. Returns {character_name: voice_print}."""
    with connect() as conn:
        chars = rows_to_dicts(
            conn.execute(
                "SELECT * FROM characters WHERE project_id = ? ORDER BY created_at",
                (project_id,),
            ).fetchall()
        )
    result = {}
    for char in chars:
        payload = char.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        name = (payload or {}).get("name") or char.get("title") or ""
        if not name:
            continue
        vp = char.get("voice_print", "{}")
        if isinstance(vp, str):
            try:
                vp = json.loads(vp)
            except json.JSONDecodeError:
                vp = {}
        result[name] = vp if isinstance(vp, dict) else {}
    return result


def update_voice_print(project_id: str, character_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Merge updates into existing voice print and persist."""
    existing = get_voice_print(project_id, character_id)
    # Merge: append to lists, replace scalars
    for key, value in updates.items():
        if key in ("speech_habits", "vocabulary_tendency", "avoid_words", "emotional_tells", "sample_dialogues"):
            existing_list = existing.get(key, [])
            if not isinstance(existing_list, list):
                existing_list = []
            if isinstance(value, list):
                for item in value:
                    if item not in existing_list:
                        existing_list.append(item)
                existing[key] = existing_list
            else:
                if value not in existing_list:
                    existing_list.append(value)
                existing[key] = existing_list
        else:
            existing[key] = value

    with connect() as conn:
        conn.execute(
            "UPDATE characters SET voice_print = ?, updated_at = ? WHERE id = ? AND project_id = ?",
            (json.dumps(existing, ensure_ascii=False), _now(), character_id, project_id),
        )
    return existing


def inject_voice_prints_into_context(context: dict[str, Any], project_id: str) -> dict[str, Any]:
    """Inject voice prints into generation context for draft generation.

    Adds 'voice_prints' key to context: {character_name: voice_print_dict}
    """
    voice_prints = get_all_voice_prints(project_id)
    if voice_prints:
        context["voice_prints"] = {
            name: {
                "speech_habits": vp.get("speech_habits", []),
                "vocabulary_tendency": vp.get("vocabulary_tendency", []),
                "avoid_words": vp.get("avoid_words", []),
                "emotional_tells": vp.get("emotional_tells", []),
            }
            for name, vp in voice_prints.items()
            if vp  # skip empty
        }
    return context


def check_voice_consistency(dialogue_map: dict[str, Any], voice_prints: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Check dialogue map against voice prints. Returns list of mismatches.

    Called during archaeology/dialogue analysis to flag voice inconsistencies.
    """
    mismatches = []
    dialogues = dialogue_map.get("dialogue_map") or []
    for d in dialogues:
        if not isinstance(d, dict):
            continue
        speaker = d.get("speaker", "")
        vp = voice_prints.get(speaker)
        if not vp:
            continue  # no voice print for this character

        line = d.get("line", "")
        issues = d.get("issues") or []

        # Check avoid_words
        avoid = vp.get("avoid_words", [])
        for word in avoid:
            if word and word in line:
                mismatches.append({
                    "speaker": speaker,
                    "line": line,
                    "issue": "voice_mismatch",
                    "detail": f"character would not say '{word}'",
                    "fix_direction": f"replace with an expression consistent with {speaker}'s voice",
                })

        # Check if issues already flagged voice_mismatch
        if "voice_mismatch" in issues:
            mismatches.append({
                "speaker": speaker,
                "line": line,
                "issue": "voice_mismatch",
                "detail": "dialogue does not match character's established voice",
                "fix_direction": "adjust to match voice print",
            })

    return mismatches


def harvest_voice_traits_from_archaeology(
    project_id: str,
    chapter_id: str,
    archaeology: dict[str, Any],
    dialogue_map: dict[str, Any],
) -> None:
    """When archaeology discovers new speech traits, write back to voice prints.

    This is the 'growth' mechanism: voice prints evolve as the story progresses.
    """
    # Extract subconscious leads that reveal speech patterns
    leads = archaeology.get("subconscious_leads") or []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        detail = lead.get("detail", "")
        inferred = lead.get("inferred", "")

        # If the lead is about a speech pattern, try to attribute it to a character
        # and update that character's voice print
        for speaker in _extract_speakers_from_dialogue(dialogue_map):
            if speaker and speaker in detail:
                # Find the character by name
                char_id = _find_character_id_by_name(project_id, speaker)
                if char_id:
                    update_voice_print(project_id, char_id, {
                        "emotional_tells": [inferred] if inferred else [],
                    })


def _extract_speakers_from_dialogue(dialogue_map: dict[str, Any]) -> list[str]:
    """Extract unique speaker names from dialogue map."""
    speakers = set()
    for d in (dialogue_map.get("dialogue_map") or []):
        if isinstance(d, dict) and d.get("speaker"):
            speakers.add(d["speaker"])
    return list(speakers)


def _find_character_id_by_name(project_id: str, name: str) -> str | None:
    """Find a character ID by name (checks payload.name and title)."""
    if not name:
        return None
    with connect() as conn:
        chars = rows_to_dicts(
            conn.execute(
                "SELECT * FROM characters WHERE project_id = ?",
                (project_id,),
            ).fetchall()
        )
    for char in chars:
        payload = char.get("payload")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        char_name = (payload or {}).get("name") or char.get("title") or ""
        if char_name == name:
            return char.get("id")
    return None


def _now() -> str:
    from ..infrastructure.database import utc_now
    return utc_now()
