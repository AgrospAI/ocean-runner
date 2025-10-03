from logging import getLogger

from pytest import fixture

from add import add

logger = getLogger(__name__)


@fixture(scope="session", autouse=True)
def setup():

    yield

    logger.info("Ending session")


def test_add():
    assert add(1, 2) == 3
