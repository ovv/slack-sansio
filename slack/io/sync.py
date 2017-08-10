import time
import requests
import websocket

from . import abc
from .. import utils


class SlackAPI(abc.SlackAPI):

    def _request(self, method, url, headers, body):

        response = requests.request(method, url, headers=headers, data=body)
        return response.status_code, response.headers, response.content

    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    def postiter(self, *args, **kwargs):
        yield from super().postiter(*args, **kwargs)

    def rtm(self):

        data = self.post('rtm.connect')
        ws = websocket.create_connection(data['url'])

        while True:
            msg = ws.recv()
            if msg:
                yield utils.parse_from_rtm(msg)
            else:
                time.sleep(0.1)
