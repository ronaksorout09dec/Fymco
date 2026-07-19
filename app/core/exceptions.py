class ApplicationError(Exception):
    status_code = 400
    error_code = "application_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NotFoundError(ApplicationError):
    status_code = 404
    error_code = "not_found"


class ConflictError(ApplicationError):
    status_code = 409
    error_code = "conflict"


class BusinessRuleError(ApplicationError):
    status_code = 400
    error_code = "business_rule_violation"


class UnauthorizedError(ApplicationError):
    status_code = 401
    error_code = "unauthorized"

