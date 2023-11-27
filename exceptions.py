class YperTechnicalTestException(Exception):
    def __init__(self, *args, error_code: str = 'Undefined error'):
        self.error_code = error_code
        super().__init__(*args)


class PhoneNumberException(YperTechnicalTestException):
    def __init__(self, *args):
        super().__init__(*args, error_code='invalid_phone_number')


class NotACellphoneNumberException(PhoneNumberException):
    pass


class ForeignPhoneNumber(PhoneNumberException):
    pass


class UnderageException(YperTechnicalTestException):
    def __init__(self, *args):
        super().__init__(*args, error_code='underage')


class UnprocessableAddressException(YperTechnicalTestException):
    def __init__(self, *args):
        super().__init__(*args, error_code='unprocessable_address')


class DeliveryTooFarException(YperTechnicalTestException):
    def __init__(self, *args):
        super().__init__(*args, error_code='delivery_too_far')


class DeliveryAbroadException(YperTechnicalTestException):
    def __init__(self, *args):
        super().__init__(*args, error_code='delivery_abroad')
