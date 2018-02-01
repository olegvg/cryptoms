import decimal
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from transer import config
from transer.exceptions import TransactionInconsistencyError
from transer.db import eth, btc, transaction, sqla_session
from transer.types import CryptoCurrency, WithdrawalStatus
from transer.btc.create_transaction import transaction_fee_per_byte, create_transaction
from transer.btc.sign_transaction import sign_transaction
from transer.btc.send_transaction import send_transaction
from transer.btc.monitor_transaction import get_txid_status


def withdraw_btc(u_txid, address, amount):
    """

    :param u_txid: UUID4 идентификатор транзакции в сервисе cryptopay
    :param address: адрес, на который нужно сделать перечилсение;
        запрещены перечисления членам системы / на адреса, принадлежащие системе используя внешнюю Bitcoin сеть
    :param amount: объём битокойнов
    :return:
    """

    # explicitly prohibit withdrawals to addresses belong to Cryptology
    # i.e. cryptopayments between clients via external Bitcoin network
    check_addr = btc.Address.query.filter(
        btc.Address.address == address
    ).count()
    if check_addr > 0:  # == 1 actually
        return WithdrawalStatus.FAILED.value

    def brand_new_transacton():
        btcd_instance_name = config['btcd_instance_name']
        key_name = config['btc_masterkey_name']
        masterkey_q = btc.MasterKey.query.filter(
            btc.MasterKey.masterkey_name == key_name
        )
        masterkey = masterkey_q.one()

        bitcoind_instance_q = btc.BitcoindInstance.query.filter(
            btc.BitcoindInstance.instance_name == btcd_instance_name
        )
        bitcoind_inst = bitcoind_instance_q.one()

        # given that num of UTXOs ~ num of Adresses and fee is ~$2 per UTXO
        # so let it be no more 10 UTXOs/Addresses to feed the destination at cost ~$20 and one wallet for change
        ordered_adresses_q = btc.Address.query.filter(
            btc.Address.bitcoind_inst == bitcoind_inst,
            btc.Address.masterkey == masterkey,
            btc.Address.address != address
        ).order_by(desc(btc.Address.amount)).limit(11)
        candidates = ordered_adresses_q.all()
        change_address = candidates.pop(-1)

        estimate_amount = decimal.Decimal(0.0)
        fee_per_byte = transaction_fee_per_byte(bitcoind_inst, preferred_blocks=5)

        # bytes = 148 * in + 34 * out + 10 ± in
        projected_fee = fee_per_byte * (148 * len(candidates) + 34 * 2 + 10 + len(candidates))

        src_address_objs = []
        for c in candidates:
            estimate_amount += c.amount
            src_address_objs.append(c)
            if estimate_amount >= amount + projected_fee:
                break
        if estimate_amount < amount + projected_fee:
            crypto_transaction.status = WithdrawalStatus.FAILED.value
            sqla_session.commit()
            return WithdrawalStatus.FAILED.value

        src_addresses = [x.address for x in src_address_objs]

        _, trx = create_transaction(
            bt_name=bitcoind_inst.instance_name,
            sources=src_addresses,
            destination=address,
            amount=amount,
            change=change_address,
            fee=projected_fee
        )

        _, signed_trx = sign_transaction(
            bt_name=bitcoind_inst.instance_name,
            signing_addrs=src_addresses,
            trx=trx
        )

        # It would be a race condition between section starting from send_transaction() to sqla_session.commit()
        # and monitor_transaction.get_recent_deposit_transactions(), if get_recent_deposit_transactions() taken
        # into account transactions with num of confirmations equals to 0 (mempool/unconfirmed transactions).
        # Doesn't actual condition now
        txid = send_transaction(
            bt_name=bitcoind_inst.instance_name,
            signed_trx=signed_trx
        )

        crypto_transaction.status = WithdrawalStatus.PENDING.value
        crypto_transaction.txids = [txid]

        change_address_log = btc.ChangeTransactionLog(
            # change_address=change_address,
            change_tx_id=txid
        )
        sqla_session.add(change_address_log)

        sqla_session.commit()
        return crypto_transaction.status

    u_txid_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = u_txid_q.one()
    except MultipleResultsFound as e:
        raise TransactionInconsistencyError(f'Multiple transaction records found for {u_txid}. Report the bug') from e
    except NoResultFound:
        crypto_transaction = transaction.CryptoWithdrawTransaction(
            u_txid=u_txid,
            currency=CryptoCurrency.BITCOIN.value,
            status=WithdrawalStatus.PENDING.value

        )
        sqla_session.add(crypto_transaction)
        sqla_session.commit()
        return brand_new_transacton()

    return crypto_transaction.status


def withdrawal_status_btc(txids):
    btcd_instance_name = config['btcd_instance_name']
    try:
        txid = txids[0]  # in btc, only one txid per transaction
    except (KeyError, TypeError):
        return WithdrawalStatus.FAILED.value

    tx_info = get_txid_status(
        bt_name=btcd_instance_name,
        txid=txid
    )

    confirmations = tx_info['confirmations']

    status = WithdrawalStatus.FAILED.value
    if confirmations >= 6:
        status = WithdrawalStatus.COMPLETED.value
    elif confirmations >= 0:
        status = WithdrawalStatus.PENDING.value

    return status


def withdraw_eth(u_txid, address, amount):
    """

    :param u_txid: UUID4 идентификатор транзакции в сервисе cryptopay
    :param address: адрес, на который нужно сделать перечилсение
    :param amount: объём битокойнов
    :return:
    """
    pass


def withdrawal_status_eth(txids):
    pass
