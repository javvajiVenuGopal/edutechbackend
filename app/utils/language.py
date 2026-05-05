from fastapi import Header
from app.utils.messages import MESSAGES


def get_message(key: str, lang: str):

    if lang not in ["en", "te"]:
        lang = "en"

    return MESSAGES[key][lang]


def language_header(accept_language: str = Header(default="en")):
    return accept_language