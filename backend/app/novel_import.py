"""导入解析：整本小说按章节切分；片段自动识别所属层并匹配章节。"""

import re
from typing import Any

# 章节标题行：第X章/回/节/卷、Chapter N、序章/楔子/尾声/番外、数字编号.
_HEADING_PATTERNS = [
    re.compile(r"^\s*序\s*章|^\s*楔\s*子|^\s*引\s*子|^\s*尾\s*声|^\s*终\s*章|^\s*番\s*外"),
    re.compile(r"^\s*第\s*[0-9零〇一二两三四五六七八九十百千万]+\s*[章回节卷][\s：:、．.，,·]?\s*\S{0,40}"),
    re.compile(r"^\s*chapter\s+\d+", re.IGNORECASE),
    re.compile(r"^\s*\d{1,4}\s*[、.．:：]\s*\S{1,40}"),
]

_MAX_HEADING_LEN = 60


def looks_like_heading(line: str) -> bool:
    text = line.strip()
    if not text or len(text) > _MAX_HEADING_LEN:
        return False
    return any(pattern.match(text) for pattern in _HEADING_PATTERNS)


def split_segments(content: str) -> list[dict[str, Any]]:
    """按标题行切分。返回 [{title, content, is_heading}]；无标题时整体是一个片段。"""
    lines = content.replace("\r\n", "\n").split("\n")
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in lines:
        if looks_like_heading(line):
            if current is not None:
                segments.append(current)
            current = {"title": line.strip(), "lines": []}
        elif current is not None:
            current["lines"].append(line)
        else:
            current = {"title": "", "lines": [line]}
    if current is not None:
        segments.append(current)
    for index, segment in enumerate(segments):
        body = "\n".join(segment.pop("lines")).strip()
        if not segment["title"] and body:
            first_line = body.split("\n", 1)[0].strip()
            if len(first_line) <= _MAX_HEADING_LEN:
                segment["title"] = first_line
        segment["content"] = body
        segment["index"] = index
        segment["words"] = len(body)
    return segments


# 摘要取正文开头前两句，控制在 160 字内.
_SUMMARY_SENTENCES = 2
_SUMMARY_MAX_CHARS = 160


def extract_summary(content: str, max_chars: int = _SUMMARY_MAX_CHARS) -> str:
    """本地抽取式摘要：取正文开头前几句拼接，不调用大模型，导入零 token。"""
    text = re.sub(r"\s+", "", content)
    if not text:
        return ""
    sentences = [sentence for sentence in re.split(r"(?<=[。！？…；])", text) if sentence]
    parts: list[str] = []
    total = 0
    for sentence in sentences:
        parts.append(sentence)
        total += len(sentence)
        if len(parts) >= _SUMMARY_SENTENCES or total >= max_chars:
            break
    summary = "".join(parts)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rstrip() + "……"
    return summary


def has_chapter_structure(content: str) -> bool:
    segments = split_segments(content)
    titled = [item for item in segments if item["title"] and looks_like_heading(item["title"])]
    # 多个标题段，或唯一标题段且正文足够长，才认为是整本/多章结构
    return len(titled) > 1 or (len(titled) == 1 and titled[0]["words"] >= 200)


_LAYER_KEYWORDS: dict[str, list[str]] = {
    "character": ["人物", "角色", "主角", "配角", "反派", "姓名", "性别", "年龄", "外貌", "性格", "身份", "背景", "师承", "门派", "口头禅"],
    "world": ["世界观", "设定", "大陆", "帝国", "王朝", "王国", "修炼", "灵气", "斗气", "魔法", "功法", "体系", "势力", "宗门", "种族", "地图", "货币", "历史", "神话", "规则"],
    "outline": ["大纲", "梗概", "主线", "支线", "伏笔", "转折", "高潮", "结局", "开篇", "第一幕", "第二幕", "第三幕", "情节线", "剧情走向", "章节规划"],
}

# 片段参与匹配/展示的长度上限，整段超长时只取开头
_FRAGMENT_SAMPLE_LEN = 1200


def classify_fragment(content: str) -> str:
    sample = content[:2000]
    scores = {
        layer: sum(sample.count(keyword) for keyword in keywords)
        for layer, keywords in _LAYER_KEYWORDS.items()
    }
    best = max(scores, key=lambda layer: scores[layer])
    return best if scores[best] > 0 else "chapter"


LAYER_LABELS = {
    "chapter": "章节正文",
    "world": "世界观设定",
    "character": "人物档案",
    "outline": "大纲",
}


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)} if len(cleaned) > 1 else {cleaned} if cleaned else set()


def _chars(text: str) -> set[str]:
    return {char for char in re.sub(r"\s+", "", text) if char not in "，。！？；：、""''…—"}


def similarity(left: str, right: str) -> float:
    left_grams, right_grams = _bigrams(left), _bigrams(right)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / len(left_grams | right_grams)


def match_chapter(content: str, chapters: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, float]:
    """在已有章节中为片段找最相似的归属；返回 (章节|None, 匹配度)。

    短片段对长章节用包含度（片段 n-gram 被章节覆盖的比例），避免长度差异压低分数；
    双字agram捕捉词面复用，单字agram补充同场景改写。匹配度取两者折算后的最大值。
    """
    sample = content[:_FRAGMENT_SAMPLE_LEN]
    fragment_grams = _bigrams(sample)
    fragment_chars = _chars(sample)
    if not fragment_grams:
        return None, 0.0
    best: dict[str, Any] | None = None
    best_score = 0.0
    for chapter in chapters:
        haystack = f"{chapter.get('title', '')} {chapter.get('summary', '')} {chapter.get('draft', '')[:2000]}"
        grams = _bigrams(haystack)
        bigram_score = len(fragment_grams & grams) / len(fragment_grams)
        unigram_score = len(fragment_chars & _chars(haystack)) / len(fragment_chars) if fragment_chars else 0.0
        score = max(bigram_score, unigram_score * 0.8)
        if score > best_score:
            best, best_score = chapter, score
    return (best, round(best_score, 4)) if best_score >= 0.25 else (None, round(best_score, 4))
