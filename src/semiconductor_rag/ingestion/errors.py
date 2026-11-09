"""수집 오류의 종류와 요청 정보를 전달한다."""


class IngestionError(Exception):
    def __init__(self, code, message, *, attempts=0, http_status=None, final_url=None):
        super().__init__(message)
        self.code = code
        self.attempts = attempts
        self.http_status = http_status
        self.final_url = final_url
