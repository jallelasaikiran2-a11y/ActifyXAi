def format_response(text: str, status: str = "success") -> dict:
    return {
        "status": status,
        "data": text
    }

def clean_selection(text: str) -> str:
    """Removes unnecessary whitespaces from selection."""
    return " ".join(text.split())
