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
