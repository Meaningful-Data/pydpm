from sqlalchemy.orm import Session
from py_dpm.dpm.models import Release
from py_dpm.dpm.queries.base import BaseQuery


class ReleaseQuery:
    """
    Queries related to releases.
    """

    @staticmethod
    def get_all_releases(session: Session) -> BaseQuery:
        """
        Fetch list of available releases.
        """
        q = session.query(Release).order_by(Release.date.desc())
        return BaseQuery(session, q)

    @staticmethod
    def get_release_by_id(session: Session, release_id: int) -> BaseQuery:
        """
        Fetch release by id.
        """
        q = session.query(Release).filter(Release.releaseid == release_id)
        return BaseQuery(session, q)

    @staticmethod
    def get_release_by_code(session: Session, release_code: str) -> BaseQuery:
        """
        Fetch release by code.
        """
        q = session.query(Release).filter(Release.code == release_code)
        return BaseQuery(session, q)
