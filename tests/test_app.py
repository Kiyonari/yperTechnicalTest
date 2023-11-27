from pprint import pprint

import pytest

from app import check_receiver_age, check_phone_number, check_payload, gmaps, get_directions, check_delivery_to_france, \
    compute_delivery_cost
from exceptions import UnderageException, DeliveryAbroadException, NotACellphoneNumberException, \
    ForeignPhoneNumber
from models import Receiver, Sender, Location


@pytest.fixture()
def test_body():
    return {
        'receiver': {
            'address': '192 Bd Victor Hugo, 59000 Lille',
            # use gmaps.geocode()
            'birthdate': '1994-04-24',
            'email': 'dummy_email@gmail.com',
            'firstname': 'Jean',
            'lastname': 'Dupont',
            'phone': '06 91 83 43 54'
        },
        'sender': {
            'lat': 50.7389877,
            'lng': 3.1370422,
            'name': 'Auchan Roncq'
            # use gmaps.reverse_geocode()
        }
    }


def test_check_payload(test_body):
    """First test is valid. Other are error tests"""
    assert check_payload(test_body) is True

    test_body['receiver']['birthdate'] = '2018-05-23'
    with pytest.raises(UnderageException) as exception:
        check_payload(test_body)
    assert exception.type == UnderageException


def test_receiver_birthdate(test_body):
    """First test is valid. Other are error tests"""
    assert check_receiver_age(test_body['receiver']) >= 18

    underage = '2021-05-23'
    test_body['receiver']['birthdate'] = underage
    assert check_receiver_age(test_body['receiver']) < 18


def test_phone_number(test_body):
    """First test is valid. Other are error tests"""
    assert check_phone_number(test_body['receiver']) is True

    household_phone = '03 20 43 48 82'
    test_body['receiver']['phone'] = household_phone
    with pytest.raises(NotACellphoneNumberException) as exc_info:
        check_phone_number(test_body['receiver'])
    assert str(exc_info.value) == "Phone number is not a cellphone"

    uk_phone = '447114513167'
    test_body['receiver']['phone'] = uk_phone
    with pytest.raises(ForeignPhoneNumber) as exc_info:
        check_phone_number(test_body['receiver'])
    assert str(exc_info.value) == "Foreign phone number"


@pytest.fixture()
def sender(test_body):
    location = Location(test_body['sender']['lat'], test_body['sender']['lng'])
    return Sender(name=test_body['sender']['name'], location=location)


@pytest.fixture()
def receiver(test_body):
    receiver = Receiver(**test_body['receiver'])
    geocode = gmaps.geocode(receiver.address)
    receiver.location = Location(**geocode[0]['geometry']['location'])
    return receiver


def test_get_directions(sender, receiver):
    directions = get_directions(sender, receiver)
    assert len(directions) > 0


def test_check_delivery_to_france(sender, receiver):
    abroad_location = gmaps.geocode('Rue Haute 84, 7700 Mouscron, Belgium')
    receiver.location = Location(**abroad_location[0]['geometry']['location'])

    with pytest.raises(DeliveryAbroadException) as exc_info:
        check_delivery_to_france(abroad_location)
    assert exc_info.type is DeliveryAbroadException


def test_compute_delivery_cost():
    """Distance in meters"""
    distance = 6000
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 8.4

    distance = 6954  # still 6km
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 8.4

    distance = 4366
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 7

    distance = 405
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 3

    distance = 2568
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 5.4

    distance = 16_235
    price = compute_delivery_cost(distance)
    assert price['total_ht'] == 16.2
    assert price['total_ttc'] == 19.44
    assert price['tva'] == 3.24
