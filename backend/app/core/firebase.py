"""Firebase Admin SDK initialization for Firestore database."""

import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)

_firebase_app = None
_firestore_client = None


@lru_cache
def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    settings = get_settings()
    if settings.database_backend != "firestore":
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app

        if settings.firebase_credentials_path:
            from pathlib import Path

            cred_path = Path(settings.firebase_credentials_path)
            if cred_path.exists():
                cred = credentials.Certificate(str(cred_path))
                _firebase_app = firebase_admin.initialize_app(cred, {
                    "projectId": settings.firebase_project_id or None,
                })
                logger.info("Firebase initialized with service account")
                return _firebase_app

        # Application default credentials (Cloud Run, GCP, FIREBASE_CONFIG env)
        _firebase_app = firebase_admin.initialize_app(options={
            "projectId": settings.firebase_project_id or None,
        })
        logger.info("Firebase initialized with default credentials")
        return _firebase_app
    except Exception as exc:
        logger.warning("Firebase init failed: %s — falling back to emulator or offline", exc)
        return None


def get_firestore():
    global _firestore_client
    if _firestore_client is not None:
        return _firestore_client

    app = get_firebase_app()
    if not app:
        return None

    from firebase_admin import firestore

    _firestore_client = firestore.client(app)
    return _firestore_client
