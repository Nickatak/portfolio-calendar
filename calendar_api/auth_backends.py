from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class UsernameOrEmailBackend(ModelBackend):
    """
    Authenticate users by either username or email.

    Django admin posts the identifier in the "username" field, so we accept
    that input and resolve against both username and email.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or kwargs.get("email")
        if identifier is None or password is None:
            return None

        user_model = get_user_model()
        try:
            user = user_model.objects.get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except user_model.DoesNotExist:
            user_model().set_password(password)
            return None
        except user_model.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
