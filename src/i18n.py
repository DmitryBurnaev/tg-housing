import gettext

from config.app import I18N_FALLBACK

t = gettext.translation(domain="messages", localedir="src/i18n", fallback=I18N_FALLBACK)
_ = t.gettext
