import re
import unicodedata

def normalize_text(text: str) -> str:
    """
    Normalize text by:
    - Converting to lowercase
    - Removing punctuation and emojis (retaining alphanumeric characters and spaces)
    - Replacing multiple spaces with a single space and trimming.
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Filter character by character
    normalized = []
    for char in text:
        # Keep letters (L), numbers (N), and whitespaces
        cat = unicodedata.category(char)
        if cat.startswith('L') or cat.startswith('N') or char.isspace():
            normalized.append(char)
            
    text_filtered = "".join(normalized)
    
    # Collapse consecutive spaces and strip
    text_collapsed = re.sub(r'\s+', ' ', text_filtered)
    return text_collapsed.strip()


def contains_keyword(comment_text: str, keyword: str, exact_word: bool = True) -> bool:
    """
    Check if a comment text contains a keyword.
    By default, exact_word uses regex word boundaries so that 'link' doesn't match 'blink'.
    """
    norm_comment = normalize_text(comment_text)
    norm_keyword = normalize_text(keyword)
    
    if not norm_keyword:
        return False
        
    if exact_word:
        # Match as full word
        pattern = r'\b' + re.escape(norm_keyword) + r'\b'
        return bool(re.search(pattern, norm_comment))
    else:
        # Match as substring
        return norm_keyword in norm_comment


from datetime import datetime, timezone
from typing import Optional, Any

def parse_iso_timestamp(ts_val: Any) -> Optional[datetime]:
    """
    Parse ISO 8601 timestamps returned by Meta APIs, handling Z suffixes
    and lack of timezone colons in older Python versions.
    """
    if not isinstance(ts_val, str):
        return None
    if ts_val.endswith("Z"):
        ts_val = ts_val[:-1] + "+00:00"
    # Convert +HHMM or -HHMM timezone offsets to +HH:MM format for Python <= 3.10
    ts_val = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', ts_val)
    try:
        dt = datetime.fromisoformat(ts_val)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        return None
