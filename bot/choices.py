from .models import AGE_RANGES, GENDERS, INTEREST_AREAS, RATING_CHOICES, INTENT_CHOICES, EMOTION_CHOICES, EMOTION_RATING_CHOICES, REGIONS, RISK_LEVEL_CHOICES

def get_choice_label(choices, code, lang='en'):
    """
    Returns the label for the given code and language.
    """
    index = 1 if lang == 'en' else 2
    for c in choices:
        if c[0] == code:
            return c[index]
    return code  # fallback

def choices_for_buttons(choices, lang='en'):
    """
    Returns list of tuples: (label, code) for Telegram buttons.
    """
    index = 1 if lang == 'en' else 2
    return [(c[index], c[0]) for c in choices]
