import hashlib
import hmac
import logging
import time
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.errors import DeserializationError, RemoteError, UnknownAsset
from rotkehlchen.exchanges.data_structures import AssetMovement, Location, MarginPosition
from rotkehlchen.exchanges.exchange import ExchangeInterface
from rotkehlchen.exchanges.utils import deserialize_asset_movement_address, get_key_if_has_val
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount_force_positive,
    deserialize_fee,
)
from rotkehlchen.typing import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    AssetMovementCategory,
    Fee,
    Timestamp,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import cache_response_timewise, protect_with_lock
from rotkehlchen.utils.misc import iso8601ts_to_timestamp, satoshis_to_btc
from rotkehlchen.utils.serialization import rlk_jsonloads

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BITMEX_PRIVATE_ENDPOINTS = (
    'user',
    'user/wallet',
    'user/walletHistory',
)


def bitmex_to_world(symbol: str) -> Asset:
    if symbol == 'XBt':
        return A_BTC
    return Asset(symbol)


def trade_from_bitmex(bitmex_trade: Dict) -> MarginPosition:
    """Turn a bitmex trade returned from bitmex trade history to our common trade
    history format. This only returns margin positions as bitmex only deals in
    margin trading"""
    close_time = iso8601ts_to_timestamp(bitmex_trade['transactTime'])
    profit_loss = AssetAmount(satoshis_to_btc(FVal(bitmex_trade['amount'])))
    currency = bitmex_to_world(bitmex_trade['currency'])
    fee = deserialize_fee(bitmex_trade['fee'])
    notes = bitmex_trade['address']
    assert currency == A_BTC, 'Bitmex trade should only deal in BTC'

    log.debug(
        'Processing Bitmex Trade',
        sensitive_log=True,
        timestamp=close_time,
        profit_loss=profit_loss,
        currency=currency,
        fee=fee,
        notes=notes,
    )

    return MarginPosition(
        location=Location.BITMEX,
        open_time=None,
        close_time=close_time,
        profit_loss=profit_loss,
        pl_currency=currency,
        fee=fee,
        fee_currency=A_BTC,
        notes=notes,
        link=str(bitmex_trade['transactID']),
    )


class Bitmex(ExchangeInterface):
    def __init__(
            self,
            api_key: ApiKey,
            secret: ApiSecret,
            database: 'DBHandler',
            msg_aggregator: MessagesAggregator,
    ):
        super().__init__('bitmex', api_key, secret, database)
        self.uri = 'https://bitmex.com'
        self.session.headers.update({'api-key': api_key})
        self.msg_aggregator = msg_aggregator

    def first_connection(self) -> None:
        self.first_connection_made = True

    def validate_api_key(self) -> Tuple[bool, str]:
        try:
            self._api_query('get', 'user')
        except RemoteError as e:
            error = str(e)
            if 'Invalid API Key' in error:
                return False, 'Provided API Key is invalid'
            if 'Signature not valid' in error:
                return False, 'Provided API Secret is invalid'
            # else reraise
            raise
        return True, ''

    def _generate_signature(self, verb: str, path: str, expires: int, data: str = '') -> str:
        signature = hmac.new(
            self.secret,
            (verb.upper() + path + str(expires) + data).encode(),
            hashlib.sha256,
        ).hexdigest()
        self.session.headers.update({
            'api-signature': signature,
        })
        return signature

    def _api_query(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Union[List, Dict]:
        """
        Queries Bitmex with the given verb for the given path and options
        """
        assert verb in ('get', 'post', 'push'), (
            'Given verb {} is not a valid HTTP verb'.format(verb)
        )

        # 20 seconds expiration
        expires = int(time.time()) + 20

        request_path_no_args = '/api/v1/' + path

        data = ''
        if not options:
            request_path = request_path_no_args
            signature_path = request_path
        else:
            request_path = request_path_no_args + '?' + urlencode(options)
            signature_path = request_path_no_args if path == 'user/wallet' else request_path

        if path in BITMEX_PRIVATE_ENDPOINTS:
            self._generate_signature(
                verb=verb,
                path=signature_path,
                expires=expires,
                data=data,
            )

        self.session.headers.update({
            'api-expires': str(expires),
        })
        if data != '':
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Content-Length': str(len(data)),
            })

        request_url = self.uri + request_path
        log.debug('Bitmex API Query', verb=verb, request_url=request_url)
        try:
            response = getattr(self.session, verb)(request_url, data=data)
        except requests.exceptions.RequestException as e:
            raise RemoteError(f'Bitmex API request failed due to {str(e)}') from e

        if response.status_code not in (200, 401):
            raise RemoteError(
                'Bitmex api request for {} failed with HTTP status code {}'.format(
                    response.url,
                    response.status_code,
                ),
            )

        try:
            json_ret = rlk_jsonloads(response.text)
        except JSONDecodeError as e:
            raise RemoteError('Bitmex returned invalid JSON response') from e

        if isinstance(json_ret, dict) and 'error' in json_ret:
            raise RemoteError(json_ret['error']['message'])

        return json_ret

    def _api_query_dict(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> Dict:
        result = self._api_query(verb, path, options)
        assert isinstance(result, Dict)  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
        return result

    def _api_query_list(
            self,
            verb: str,
            path: str,
            options: Optional[Dict] = None,
    ) -> List:
        result = self._api_query(verb, path, options)
        assert isinstance(result, List)  # pylint: disable=isinstance-second-argument-not-valid-type  # noqa: E501
        return result

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self) -> Tuple[Optional[dict], str]:

        try:
            resp = self._api_query_dict('get', 'user/wallet', {'currency': 'XBt'})
            # Bitmex shows only BTC balance
            returned_balances = {}
            usd_price = Inquirer().find_usd_price(A_BTC)
        except RemoteError as e:
            msg = f'Bitmex API request failed due to: {str(e)}'
            log.error(msg)
            return None, msg

        # result is in satoshis
        amount = satoshis_to_btc(FVal(resp['amount']))
        usd_value = amount * usd_price

        returned_balances[A_BTC] = {
            'amount': amount,
            'usd_value': usd_value,
        }
        log.debug(
            'Bitmex balance query result',
            sensitive_log=True,
            currency='BTC',
            amount=amount,
            usd_value=usd_value,
        )

        return returned_balances, ''

    def query_online_margin_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[MarginPosition]:

        # We know user/walletHistory returns a list
        resp = self._api_query_list('get', 'user/walletHistory')
        log.debug('Bitmex trade history query', results_num=len(resp))

        margin_trades = []
        for tx in resp:
            if tx['timestamp'] is None:
                timestamp = None
            else:
                timestamp = iso8601ts_to_timestamp(tx['timestamp'])
            if tx['transactType'] != 'RealisedPNL':
                continue
            if timestamp and timestamp < start_ts:
                continue
            if timestamp and timestamp > end_ts:
                continue
            margin_trades.append(trade_from_bitmex(tx))

        return margin_trades

    def query_online_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List:
        resp = self._api_query_list('get', 'user/walletHistory')

        log.debug('Bitmex deposit/withdrawals query', results_num=len(resp))

        movements = []
        for movement in resp:
            try:
                transaction_type = movement['transactType']
                if transaction_type == 'Deposit':
                    transaction_type = AssetMovementCategory.DEPOSIT
                elif transaction_type == 'Withdrawal':
                    transaction_type = AssetMovementCategory.WITHDRAWAL
                else:
                    continue

                timestamp = iso8601ts_to_timestamp(movement['timestamp'])
                if timestamp < start_ts:
                    continue
                if timestamp > end_ts:
                    continue

                asset = bitmex_to_world(movement['currency'])
                amount = deserialize_asset_amount_force_positive(movement['amount'])
                fee = deserialize_fee(movement['fee'])

                if asset == A_BTC:
                    # bitmex stores amounts in satoshis
                    amount = AssetAmount(satoshis_to_btc(amount))
                    fee = Fee(satoshis_to_btc(fee))

                movements.append(AssetMovement(
                    location=Location.BITMEX,
                    category=transaction_type,
                    address=deserialize_asset_movement_address(movement, 'address', asset),
                    transaction_id=get_key_if_has_val(movement, 'tx'),
                    timestamp=timestamp,
                    asset=asset,
                    amount=amount,
                    fee_asset=asset,
                    fee=fee,
                    link=str(movement['transactID']),
                ))
            except UnknownAsset as e:
                self.msg_aggregator.add_warning(
                    f'Found bitmex deposit/withdrawal with unknown asset '
                    f'{e.asset_name}. Ignoring it.',
                )
                continue
            except (DeserializationError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'Missing key entry for {msg}.'
                self.msg_aggregator.add_error(
                    'Unexpected data encountered during deserialization of a bitmex '
                    'asset movement. Check logs for details and open a bug report.',
                )
                log.error(
                    f'Unexpected data encountered during deserialization of bitmex '
                    f'asset_movement {movement}. Error was: {msg}',
                )
                continue
        return movements
