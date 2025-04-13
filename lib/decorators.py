from functools import wraps
from pyteal import (
    If,
    Int,
    Return,
    Seq,
    Subroutine,
    TealType,
    Txn,
)

from lib.err import err_unauthorized, err_not_ready
from lib.storage import gget
from lib.str import str_admin_addr, str_fee_addr, str_lst_id, str_noderunner_addr
from lib.utils import custom_assert


#
# single role subroutine guards
#


# avalidate caller is admin
@Subroutine(TealType.none)
def assert_admin():
    """
    fails if the caller is not the contract admin
    """
    return custom_assert(Txn.sender() == gget(str_admin_addr), err_unauthorized)


@Subroutine(TealType.none)
def assert_fee_admin():
    """
    fails if the caller is not the fee admin address
    """
    return custom_assert(Txn.sender() == gget(str_fee_addr), err_unauthorized)


@Subroutine(TealType.none)
def assert_node_runner():
    """
    fails if the caller is not the node runner address
    """
    return custom_assert(Txn.sender() == gget(str_noderunner_addr), err_unauthorized)


#
# combination role subroutine guards
#


@Subroutine(TealType.none)
def assert_admin_or_fee_admin():
    """
    fails if the caller is not admin or fee admin
    """
    return If(Txn.sender() == gget(str_fee_addr)).Then(Return()).Else(assert_admin())


@Subroutine(TealType.none)
def assert_fee_admin_or_node_runner():
    """
    fails if the caller is not noderunner or fee admin
    """
    return (
        If(Txn.sender() == gget(str_noderunner_addr))
        .Then(Return())
        .Else(assert_fee_admin())
    )


#
# Decorators. Apply AFTER @router.method
#

def ready(fn):
    """
    When contract is ready i.e. LST has been created
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(
            custom_assert(gget(str_lst_id) != Int(0), err_not_ready),
            fn(*args, **kwds),
        )

    return wrapper


def admin_only(fn):
    """
    Admin method only
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(assert_admin(), fn(*args, **kwds))

    return wrapper


def fee_admin_only(fn):
    """
    fee admin only
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(assert_fee_admin(), fn(*args, **kwds))

    return wrapper


def node_runner_only(fn):
    """
    node runner only
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(assert_node_runner(), fn(*args, **kwds))

    return wrapper


def admin_or_fee_admin_only(fn):
    """
    admin or fee admin roles only
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(assert_admin_or_fee_admin(), fn(*args, **kwds))

    return wrapper


def fee_admin_or_node_runner_only(fn):
    """
    fee admin or node runner only
    """
    @wraps(fn)
    def wrapper(*args, **kwds):
        return Seq(assert_fee_admin_or_node_runner(), fn(*args, **kwds))

    return wrapper
