import math
import os
from datetime import date

import flask
import googlemaps
from dotenv import load_dotenv
import phonenumbers
from flask import Flask, request, Response
from flask_cors import CORS

from exceptions import DeliveryTooFarException, UnderageException, YperTechnicalTestException, \
    UnprocessableAddressException, DeliveryAbroadException, NotACellphoneNumberException, ForeignPhoneNumber
from models import Receiver, Location, Sender

load_dotenv()

yperApp = Flask(__name__)
CORS(yperApp)
cors = CORS(yperApp)
yperApp.config['CORS_HEADERS'] = 'Content-Type'
gmaps = googlemaps.Client(key=os.getenv('GOOGLE_MAPS_API_KEY'))


def check_receiver_age(receiver: dict) -> int:
    """Returns the receiver's age based on their birthdate.

    :param receiver: json dict with a 'birthdate' field
    :type receiver: dict

    :rtype: int
    :return: age of the receiver
    """
    today = date.today()
    birthdate = date.fromisoformat(receiver['birthdate'])
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def check_phone_number(receiver: dict) -> bool:
    """Checks if phone is french and valid but does not check if it is actually used.

    :param receiver: json dict with a 'phone' field
    :type receiver: dict

    :rtype: bool
    :return: True if the phone number is valid. Raises if not.
    """
    phone = phonenumbers.parse(receiver['phone'], 'FR')
    if not phonenumbers.is_possible_number_string(receiver['phone'], 'FR'):
        raise ForeignPhoneNumber('Foreign phone number')
    if int(str(phone.national_number)[:1]) not in [6, 7]:
        raise NotACellphoneNumberException('Phone number is not a cellphone')
    return True


def check_payload(payload: dict) -> bool:
    """
    Home of error handling. Calls for various payload checks and returns accordingly.
    Further check can be made on the payload later if the need arises.

    :param payload: json dict
    :type payload: dict

    :return: True if all checks are valid
    :rtype: bool
    """
    if check_receiver_age(payload['receiver']) < 18:
        raise UnderageException()
    check_phone_number(payload['receiver'])
    return True


def check_delivery_to_france(geocode: list) -> bool:
    """Checks if the delivery destination is in France. Raises an error if not.

    :param geocode: a googlemaps geocode object with a list of points.
    :type geocode: list

    :rtype: bool
    :return: True
    """
    to_france = False
    for r in geocode[0]['address_components']:
        if 'country' in r['types'] and 'France' in r['long_name']:
            to_france = True

    if not to_france:
        raise DeliveryAbroadException()
    return True


def get_directions(sender: Sender, receiver: Receiver) -> list:
    """Requests every instructions to reach the destination.

    :param sender: Departure point of the delivery.
    :type sender: Sender

    :param receiver: Contains all info about the customer.
    :type receiver: Receiver

    :return: A googlemap directions object. It contains every points to pass to reach the destination.
    :rtype: list
    """
    directions = gmaps.directions(
        origin=sender.location.as_tuple(),
        destination=receiver.location.as_tuple(),
        mode='driving',
        units='metric',
        region='fr'
    )
    if len(directions) == 0:
        raise UnprocessableAddressException()
    if directions[0]['legs'][0]['distance']['value'] > 20_000:
        raise DeliveryTooFarException()
    return directions


def get_map_link(sender: Sender, receiver: Receiver, directions: list) -> str:
    """Produce a static map url from google maps

    :param sender: Departure point of the delivery.
    :type sender: Sender

    :param receiver: Contains all info about the customer.
    :type receiver: Receiver

    :param directions:
    :type directions:

    :return: The url towards a static map of the delivery route.
    :rtype: str
    """
    url = f'https://maps.google.com/maps/api/staticmap?size=500x500'
    marker_sender = f'&markers=label:A|{sender.get_location()}'
    marker_receiver = f'&markers=label:B|{receiver.get_location()}'
    url += f'{marker_sender}{marker_receiver}'
    url += f'&path=enc:{directions[0]['overview_polyline']['points']}'
    url += f'&key={os.getenv('GOOGLE_MAPS_API_KEY')}'
    return url


def compute_delivery_cost(distance: int) -> dict:
    """
        Compute price per kilometers following our pricing table.

        :param distance: The distance between the start point and destination of the delivery route, in meters
        :type distance: int

        :return: The price object containing the price excluding tax, the tax price and the total price
        :rtype: dict
    """
    base_price = 3
    additional_cost = 0
    distance = math.floor(distance / 1000)  # Adjust the distance by dividing it by 10000

    if distance <= 2:
        additional_cost = distance * 1.2
    elif 3 <= distance <= 5:
        additional_cost = 2 * 1.2 + (distance - 2) * 0.8
    elif 6 <= distance <= 10:
        additional_cost = 2 * 1.2 + 3 * 0.8 + (distance - 5) * 0.6
    elif 11 <= distance <= 20:
        additional_cost = 2 * 1.2 + 3 * 0.8 + 5 * 0.6 + (distance - 10) * 0.9

    total_excluding_tax = base_price + additional_cost
    tax = 0.2 * total_excluding_tax
    price = {
        'total_ht': round(total_excluding_tax, 2),
        'tva': round(tax, 2),
        'total_ttc': round(total_excluding_tax + tax, 2),
    }
    return price


@yperApp.post('/bookdelivery')
def call() -> Response:
    check_payload(request.json)

    receiver = Receiver(**request.json['receiver'])
    location = Location(lat=request.json['sender']['lat'], lng=request.json['sender']['lng'])
    sender = Sender(name=request.json['sender']['name'], location=location)
    sender_address = gmaps.reverse_geocode(sender.get_location())

    geocode = gmaps.geocode(receiver.address)
    check_delivery_to_france(geocode)
    receiver.location = Location(**geocode[0]['geometry']['location'])
    directions = get_directions(sender, receiver)
    map_link = get_map_link(sender, receiver, directions)
    price = compute_delivery_cost(directions[0]['legs'][0]['distance']['value'])
    response = {
        'map': map_link,
        'distance': directions[0]['legs'][0]['distance']['value'],
        'pickup_address': sender_address[0]['formatted_address'],
        'delivery_address': receiver.address,
        'customer_firstname': receiver.firstname,
        'customer_lastname': receiver.lastname,
        'customer_email': receiver.email,
        'customer_phone': receiver.phone,
        'customer_birthdate': receiver.birthdate,
        'price': price,
    }
    return flask.jsonify(response)


@yperApp.errorhandler(YperTechnicalTestException)
def handler(error: YperTechnicalTestException) -> Response:
    """Handles every custom exception with a custom error_code."""
    response = flask.jsonify({
        'error_code': error.error_code
    })
    response.status_code = 400
    return response


if __name__ == '__main__':
    yperApp.run()
