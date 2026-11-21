class AnalyzerError(Exception):
    pass


class InvalidRepositoryError(AnalyzerError):
    pass


class RepositoryNotFoundError(AnalyzerError):
    pass


class RateLimitError(AnalyzerError):
    def __init__(self, message: str, reset_at: int | None = None):
        super().__init__(message)
        self.reset_at = reset_at


class GitHubAPIError(AnalyzerError):
    pass


class AuthenticationError(GitHubAPIError):
    pass


class EmptyRepositoryError(AnalyzerError):
    pass


class LLMError(AnalyzerError):
    pass
