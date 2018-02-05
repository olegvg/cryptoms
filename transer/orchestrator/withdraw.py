import decimal
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from transer import config
from transer.exceptions import TransactionInconsistencyError
from transer.db import eth, btc, transaction, sqla_session
from transer.types import CryptoCurrency, WithdrawalStatus
from transer.btc.create_transaction import calculate_transaction_fee, create_transaction
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

    u_txid_q = transaction.CryptoWithdrawTransaction.query.filter(
        transaction.CryptoWithdrawTransaction.u_txid == u_txid
    )

    try:
        crypto_transaction = u_txid_q.one()
        return crypto_transaction.status
    except MultipleResultsFound as e:
        raise TransactionInconsistencyError(f'Multiple transaction records found for {u_txid}. Report the bug') from e
    except NoResultFound:
        crypto_transaction = transaction.CryptoWithdrawTransaction(
            u_txid=u_txid,
            currency=CryptoCurrency.BITCOIN.value,
            status=WithdrawalStatus.FAILED.value

        )
        sqla_session.add(crypto_transaction)

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

        # given that num of UTXOs ~ num of Addresses and fee is ~$2 per UTXO
        # so let it be no more 10 UTXOs/Addresses to feed the destination at cost ~$20 and one wallet for change
        ordered_adresses_q = btc.Address.query.filter(
            btc.Address.bitcoind_inst == bitcoind_inst,
            btc.Address.masterkey == masterkey,
            btc.Address.address != address
        ).order_by(desc(btc.Address.amount)).limit(11)
        candidates = ordered_adresses_q.all()

        change_address = candidates.pop(-1)

        estimate_amount = decimal.Decimal(0.0)

        projected_fee = calculate_transaction_fee(
            bt_name=btcd_instance_name,
            sources=[c.address for c in candidates], destination=address,
            change=change_address.address,
            preferred_blocks=5  # Anton don't like such numbers :-)
        )
        print(projected_fee)

        src_address_objs = []
        for c in candidates:
            estimate_amount += c.amount
            src_address_objs.append(c)
            if estimate_amount > amount + projected_fee:
                break
        if estimate_amount < amount + projected_fee:
            crypto_transaction.status = WithdrawalStatus.FAILED.value
            sqla_session.commit()
            return WithdrawalStatus.FAILED.value

        src_addresses = [x.address for x in src_address_objs]

        # Equation 'projected_fee >= actual_fee' is always true
        actual_fee = calculate_transaction_fee(
            bt_name=btcd_instance_name,
            sources=[src_addresses],
            destination=address,
            change=change_address.address,
            preferred_blocks=5  # Anton don't like such numbers :-)
        )

        trx, _ = create_transaction(
            bt_name=bitcoind_inst.instance_name,
            sources=src_addresses,
            destination=address,
            amount=amount,
            change=change_address.address,
            fee=actual_fee
        )

        signed_trx, _ = sign_transaction(
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

        # change_address_log = btc.ChangeTransactionLog(
        #     # change_address=change_address,
        #     change_tx_id=txid
        # )
        # sqla_session.add(change_address_log)

        # all the funds move to change address
        for a in src_address_objs:
            a.amount = decimal.Decimal(0.0)

        sqla_session.commit()
        return crypto_transaction.status


def withdrawal_status_btc(crypto_transaction):
    btcd_instance_name = config['btcd_instance_name']

    try:
        txid = crypto_transaction.txids[0]  # in btc, only one txid per transaction
    except (KeyError, TypeError):
        return WithdrawalStatus.FAILED.value

    tx_info = get_txid_status(
        bt_name=btcd_instance_name,
        txid=txid
    )

    confirmations = tx_info['confirmations']

    if confirmations >= 6 and crypto_transaction.status != WithdrawalStatus.COMPLETED.value:
        crypto_transaction.status = WithdrawalStatus.COMPLETED.value
        crypto_transaction.is_acknowledged = False
    elif confirmations >= 0 and crypto_transaction.status != WithdrawalStatus.PENDING.value:
        crypto_transaction.status = WithdrawalStatus.PENDING.value
        crypto_transaction.is_acknowledged = False


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
