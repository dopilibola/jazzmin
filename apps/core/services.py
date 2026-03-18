from apps.core.models import Setting


def get_setting_value(key, default=''):
    return Setting.get_value(key, default)
