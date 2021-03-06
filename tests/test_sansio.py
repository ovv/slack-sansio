import time

import pytest

from slack import sansio, exceptions, methods, events

TEST_TOKEN = 'abcdefghijklmnopqrstuvwxyz'


class TestRequest:
    def test_prepare_request(self):
        url, body, headers = sansio.prepare_request(methods.AUTH_TEST, {}, {}, {}, TEST_TOKEN)
        assert url == 'https://slack.com/api/auth.test'
        assert body == {'token': TEST_TOKEN}
        assert headers == {}

    def test_prepare_request_urls(self):
        url1, _, _ = sansio.prepare_request(methods.AUTH_TEST, {}, {}, {}, '')
        url2, _, _ = sansio.prepare_request('auth.test', {}, {}, {}, '')
        url3, _, _ = sansio.prepare_request('https://slack.com/api/auth.test', {}, {}, {}, '')

        assert url1 == url2 == url3 == 'https://slack.com/api/auth.test'

    def test_prepare_request_body(self):
        data1 = {'hello': 'world'}
        data2 = data1.copy()
        data3 = data2.copy()

        _, body1, _ = sansio.prepare_request(methods.AUTH_TEST, data1, {}, {}, TEST_TOKEN)
        _, body2, _ = sansio.prepare_request('https://hooks.slack.com/abcdefg', data2, {}, {}, TEST_TOKEN)
        _, body3, _ = sansio.prepare_request('', data3, {}, {}, TEST_TOKEN)

        assert body1 == {'hello': 'world', 'token': TEST_TOKEN}
        assert body2 == '{"hello": "world", "token": "abcdefghijklmnopqrstuvwxyz"}'
        assert body3 == {'hello': 'world', 'token': TEST_TOKEN}

    def test_prepare_request_headers(self):
        headers = {'hello': 'world', 'python': '3.7'}
        global_headers = {'hello': 'python', 'sans': 'I/O'}

        _, _, prepared_header = sansio.prepare_request('', {}, headers, {}, '')
        _, _, prepared_header_with_global = sansio.prepare_request('', {}, headers, global_headers, '')

        assert prepared_header == {'hello': 'world', 'python': '3.7'}
        assert prepared_header_with_global == {'hello': 'world', 'sans': 'I/O', 'python': '3.7'}

    def test_prepare_request_serialize_message(self):
        msg = events.Message()
        msg['text'] = 'hello world'

        _, data, _ = sansio.prepare_request('', msg, {}, {}, '')
        assert data == {'token': '', 'text': 'hello world'}

    def test_find_iteration(self):
        itermode, iterkey = sansio.find_iteration(methods.CHANNELS_LIST)
        assert itermode == methods.CHANNELS_LIST.value[1]
        assert iterkey == methods.CHANNELS_LIST.value[2]

    def test_find_iteration_custom_itermode(self):
        itermode, iterkey = sansio.find_iteration(methods.CHANNELS_LIST, itermode='timeline')
        assert itermode == 'timeline'
        assert iterkey == methods.CHANNELS_LIST.value[2]

    def test_find_iteration_custom_iterkey(self):
        itermode, iterkey = sansio.find_iteration(methods.CHANNELS_LIST, iterkey='users')
        assert itermode == methods.CHANNELS_LIST.value[1]
        assert iterkey == 'users'

    def test_find_iteration_not_found(self):
        with pytest.raises(ValueError):
            _, _ = sansio.find_iteration('')

    def test_find_iteration_wrong_mode(self):
        with pytest.raises(ValueError):
            _, _ = sansio.find_iteration('', itermode='python', iterkey='users')

    def test_prepare_iter_request(self):
        data, iterkey, itermode = sansio.prepare_iter_request(methods.CHANNELS_LIST, {})
        assert data == {'limit': 200}
        assert itermode == methods.CHANNELS_LIST.value[1]
        assert iterkey == methods.CHANNELS_LIST.value[2]

    def test_prepare_iter_request_no_iterkey(self):
        data, iterkey, itermode = sansio.prepare_iter_request(methods.CHANNELS_LIST, {})
        assert data == {'limit': 200}
        assert itermode == methods.CHANNELS_LIST.value[1]
        assert iterkey == methods.CHANNELS_LIST.value[2]

    def test_prepare_iter_request_cursor(self):
        data1, _, _ = sansio.prepare_iter_request('', {}, itermode='cursor', iterkey='channels', itervalue='abcdefg')
        assert data1 == {'limit': 200, 'cursor': 'abcdefg'}

        data2, _, _ = sansio.prepare_iter_request('', {}, itermode='cursor', itervalue='abcdefg', iterkey='channels',
                                                  limit=300)
        assert data2 == {'limit': 300, 'cursor': 'abcdefg'}

    def test_prepare_iter_request_page(self):
        data1, _, _ = sansio.prepare_iter_request('', {}, itermode='page', iterkey='channels', itervalue='abcdefg')
        assert data1 == {'count': 200, 'page': 'abcdefg'}

        data2, _, _ = sansio.prepare_iter_request('', {}, itermode='page', itervalue='abcdefg', iterkey='channels',
                                                  limit=300)
        assert data2 == {'count': 300, 'page': 'abcdefg'}

    def test_prepare_iter_request_timeline(self):
        data1, _, _ = sansio.prepare_iter_request('', {}, itermode='timeline', iterkey='channels', itervalue='abcdefg')
        assert data1 == {'count': 200, 'latest': 'abcdefg'}

        data2, _, _ = sansio.prepare_iter_request('', {}, itermode='timeline', itervalue='abcdefg', iterkey='channels',
                                                  limit=300)
        assert data2 == {'count': 300, 'latest': 'abcdefg'}


class TestResponse:
    def test_raise_for_status_200(self):
        try:
            sansio.raise_for_status(200, {}, {})
        except Exception as exc:
            raise pytest.fail('RAISE {}'.format(exc))

    def test_raise_for_status_400(self):
        with pytest.raises(exceptions.HTTPException):
            sansio.raise_for_status(400, {}, {})

    def test_raise_for_status_400_httpexception(self):
        with pytest.raises(exceptions.HTTPException) as exc:
            sansio.raise_for_status(400, {'test-header': 'hello'}, {'test-data': 'world'})

        assert exc.type == exceptions.HTTPException
        assert exc.value.status == 400
        assert exc.value.headers == {'test-header': 'hello'}
        assert exc.value.data == {'test-data': 'world'}

    def test_raise_for_status_429(self):
        with pytest.raises(exceptions.RateLimited) as exc:
            sansio.raise_for_status(429, {}, {})

        assert exc.type == exceptions.RateLimited
        assert exc.value.retry_after == 1

    def test_raise_for_status_429_headers(self):

        headers = {'Retry-After': '10'}

        with pytest.raises(exceptions.RateLimited) as exc:
            sansio.raise_for_status(429, headers, {})

        assert exc.type == exceptions.RateLimited
        assert exc.value.retry_after == 10

    def test_raise_for_status_429_wrong_headers(self):
        headers = {'Retry-After': 'aa'}

        with pytest.raises(exceptions.RateLimited) as exc:
            sansio.raise_for_status(429, headers, {})

        assert exc.type == exceptions.RateLimited
        assert exc.value.retry_after == 1

    def test_raise_for_api_error_ok(self):
        try:
            sansio.raise_for_api_error({}, {'ok': True})
        except Exception as exc:
            raise pytest.fail('RAISE {}'.format(exc))

    def test_raise_for_api_error_nok(self):

        data = {'ok': False}
        headers = {'test-header': 'hello'}

        with pytest.raises(exceptions.SlackAPIError) as exc:
            sansio.raise_for_api_error(headers, data)

        assert exc.type == exceptions.SlackAPIError
        assert exc.value.headers == {'test-header': 'hello'}
        assert exc.value.data == {'ok': False}
        assert exc.value.error == 'unknow_error'

    def test_raise_for_api_error_nok_with_error(self):

        data = {'ok': False, 'error': 'test_error'}

        with pytest.raises(exceptions.SlackAPIError) as exc:
            sansio.raise_for_api_error({}, data)

        assert exc.type == exceptions.SlackAPIError
        assert exc.value.error == 'test_error'

    def test_raise_for_api_error_warning(self, capsys):

        data = {'ok': True, 'warning': 'test warning'}

        sansio.raise_for_api_error({}, data)
        _, err = capsys.readouterr()
        assert err == 'Slack API WARNING: test warning\n'

    def test_decode_body(self):
        body = b'hello world'
        decoded_body = sansio.decode_body({}, body)
        assert decoded_body == 'hello world'

    def test_decode_body_json(self):
        body = b'{"test-string":"hello","test-bool":true}'
        headers = {'content-type': 'application/json; charset=utf-8'}
        decoded_body = sansio.decode_body(headers, body)
        assert decoded_body == {"test-string": "hello", "test-bool": True}

    def test_decode_body_json_no_charset(self):
        body = b'{"test-string":"hello","test-bool":true}'
        headers = {'content-type': 'application/json'}
        decoded_body = sansio.decode_body(headers, body)
        assert decoded_body == {"test-string": "hello", "test-bool": True}

    def test_decode_response(self):
        headers = {'content-type': 'application/json; charset=utf-8'}
        data = b'{"ok": true, "hello": "world"}'
        try:
            data = sansio.decode_response(200, headers, data)
        except Exception as exc:
            pytest.fail('RAISE {}'.format(exc))
        else:
            assert data == {'ok': True, 'hello': 'world'}

    def test_decode_iter_request_cursor(self):

        data = {'response_metadata': {'next_cursor': 'abcdefg'}}
        cursor = sansio.decode_iter_request(data)
        assert cursor == 'abcdefg'

    def test_decode_iter_request_paging(self):

        data = {'paging': {'page': 2, 'pages': 4}}
        page = sansio.decode_iter_request(data)
        assert page == 3

    def test_decode_iter_request_timeline(self):

        timestamp = time.time()
        latest = timestamp - 1000
        data = {'has_more': True,
                'latest': timestamp,
                'messages': [{'ts': latest}]}
        next = sansio.decode_iter_request(data)
        assert next == latest


class TestIncomingEvent:
    def test_discard_event(self):
        for event in [
            events.Event({'type': 'reconnect_url'}),
            events.Message({'type': 'message', 'bot_id': 'B1234'}),
            events.Message({'type': 'message', 'message': {'bot_id': 'B1234'}})
        ]:
            assert sansio.discard_event(event, 'B1234') is True

        for event in [
            events.Event({'type': 'channel_joined'}),
            events.Message({'type': 'message', 'bot_id': 'B5555'}),
            events.Message({'type': 'message', 'user_id': 'U5555'}),
            events.Message({'type': 'message', 'message': {'bot_id': 'B5555'}})
        ]:
            assert sansio.discard_event(event, 'B1234') is False

    def test_need_reconnect(self):

        for event in [
            events.Event({'type': 'channel_joined'}),
            events.Message({'type': 'message', 'bot_id': 'B5555'})
        ]:
            assert sansio.need_reconnect(event) is False

        for event in [
            events.Event({'type': 'goodbye'}),
            events.Message({'type': 'team_migration_started'})
        ]:
            assert sansio.need_reconnect(event) is True
