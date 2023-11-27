from dataclasses import dataclass


@dataclass
class Location:
    lat: float
    lng: float

    def __str__(self) -> str:
        return f'{self.lat},{self.lng}'

    def as_tuple(self) -> tuple:
        return self.lat, self.lng


@dataclass
class Receiver:
    firstname: str
    lastname: str
    email: str
    phone: str
    birthdate: str
    address: str
    location: Location = None

    def __str__(self) -> str:
        return f'{self.firstname} {self.lastname}'

    def get_location(self):
        return f'{self.location}'


@dataclass
class Sender:
    name: str
    location: Location

    def __str__(self) -> str:
        return self.name

    def get_location(self):
        return f'{self.location}'
