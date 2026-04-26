class WorldForkError(Exception):
    """Base application error."""


class NotFoundError(WorldForkError):
    pass


class ValidationError(WorldForkError):
    pass


class ConflictError(WorldForkError):
    pass
