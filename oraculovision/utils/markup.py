"""Safe embedding of user/node text inside Textual markup."""


def safe_markup_text(text: str) -> str:
    """Escape arbitrary text so square brackets are not parsed as markup tags.

    Textual's built-in ``escape()`` only handles tags that look like
    ``[word...]``. Miner tags often start with ``[8j...`` (digit after bracket)
    and still break the markup parser.
    """
    return text.replace("\\", "\\\\").replace("[", "\\[")