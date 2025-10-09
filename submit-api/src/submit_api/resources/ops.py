# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Endpoints to check and manage the health of the service."""
import random
import time

from flask_restx import Namespace, Resource
from sqlalchemy import exc, text

from submit_api.models import db


API = Namespace('OPS', description='Service - OPS checks')

SQL = text('select 1')


@API.route('healthz')
class Healthz(Resource):
    """Determines if the service and required dependencies are still working.

    This could be thought of as a heartbeat for the service.
    """

    @staticmethod
    def get():
        """Return a JSON object stating the health of the Service and dependencies."""
        try:
            db.session.execute(SQL)
        except exc.SQLAlchemyError:
            return {'message': 'api is down'}, 500

        # made it here, so all checks passed
        return {'message': 'api is healthy'}, 200


@API.route('readyz')
class Readyz(Resource):
    """Determines if the service is ready to respond."""

    @staticmethod
    def get():
        """Return a JSON object that identifies if the service is setupAnd ready to work."""
        # TODO: add a poll to the DB when called
        return {'message': 'api is ready'}, 200


@API.route('delay/<int:milliseconds>')
class Delay(Resource):
    """Introduce an artificial delay before responding."""

    @staticmethod
    def get(milliseconds):
        """Sleep for the requested number of milliseconds, then respond."""
        if milliseconds < 0:
            return {'message': 'milliseconds must be non-negative'}, 400

        time.sleep(milliseconds / 1000.0)
        return {'message': f'delayed for {milliseconds} milliseconds'}, 200


@API.route('random-message')
class RandomMessage(Resource):
    """Return one of several canned messages."""

    _MESSAGES = (
        'All systems operational.',
        'Processing request in background.',
        'Worker heartbeat received.',
        'Simulated task complete.',
        'Queue depth within thresholds.',
        'Background job dispatched.',
        'Awaiting worker acknowledgment.',
        'Thread pool warmed up.',
    )

    @staticmethod
    def get():
        """Return a random message to help test downstream handling."""
        return {'message': random.choice(RandomMessage._MESSAGES)}, 200
