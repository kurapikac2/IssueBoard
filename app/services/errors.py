class ServiceError(Exception):
    """A business failure that the HTTP layer translates into a response."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)