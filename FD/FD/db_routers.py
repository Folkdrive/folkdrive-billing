# FD/db_routers.py
class LegacyRouter:
    """
    A router to control all database operations on legacy models
    """
    def db_for_read(self, model, **hints):
        """
        Attempts to read legacy models go to legacy_mysql.
        """
        if model._meta.app_label == 'FD' and hasattr(model, '_legacy'):
            return 'legacy_mysql'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write legacy models go to legacy_mysql.
        """
        if model._meta.app_label == 'FD' and hasattr(model, '_legacy'):
            return 'legacy_mysql'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if both models are in the same database.
        """
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure legacy models only appear in the 'legacy_mysql' database.
        """
        return True