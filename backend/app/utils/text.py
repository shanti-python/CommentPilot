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
    Parse ISO 8601 timestamps returned by Meta APIs, handling Z suffixes,
    unix timestamps (int/float or numeric string), datetime objects, etc.
    """
    if ts_val is None or ts_val == "":
        return None

    if isinstance(ts_val, datetime):
        return ts_val.replace(tzinfo=None) if ts_val.tzinfo else ts_val

    if isinstance(ts_val, (int, float)):
        try:
            sec = ts_val / 1000.0 if ts_val > 1e11 else float(ts_val)
            dt = datetime.fromtimestamp(sec, tz=timezone.utc)
            return dt.replace(tzinfo=None)
        except Exception:
            return None

    if isinstance(ts_val, str):
        ts_str = ts_val.strip()
        if not ts_str:
            return None

        # Check for numeric string (Unix timestamp)
        if ts_str.isdigit() or (ts_str.replace('.', '', 1).isdigit() and ts_str.count('.') <= 1):
            try:
                num = float(ts_str)
                sec = num / 1000.0 if num > 1e11 else num
                dt = datetime.fromtimestamp(sec, tz=timezone.utc)
                return dt.replace(tzinfo=None)
            except Exception:
                pass

        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"

        # Convert +HHMM or -HHMM timezone offsets to +HH:MM format
        ts_str = re.sub(r'([+-]\d{2})(\d{2})$', r'\1:\2', ts_str)

        try:
            dt = datetime.fromisoformat(ts_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    clean_str = ts_str.split('+')[0].split('-')[0].split('.')[0] if '+' in ts_str else ts_str.split('.')[0]
                    return datetime.strptime(clean_str, fmt)
                except ValueError:
                    continue
            return None

    return None
