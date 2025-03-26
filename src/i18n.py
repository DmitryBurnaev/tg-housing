import gettext

from src.config.app import I18N_FALLBACK, LOCALE_PATH

t = gettext.translation(domain="messages", localedir=LOCALE_PATH, fallback=I18N_FALLBACK)
_ = t.gettext
