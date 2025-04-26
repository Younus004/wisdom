import firebase_admin
from firebase_admin import credentials, auth, firestore

# Point to your service account
SERVICE_ACCOUNT = r"D:\wisdom\wisdom-schools-firebase-adminsdk-fbsvc-971bbaec20.json"

# Initialize (idempotent)
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred)

# Expose clients
db = firestore.client()
admin_auth = auth
