
import firebase_admin
from firebase_admin import credentials, firestore

# Path to your Firebase Admin SDK key
key_path = "D:/wisdom/wisdom-schools-firebase-adminsdk-fbsvc-016b29c3cf.json"

# Initialize Firebase
cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)

# Connect to Firestore
db = firestore.client()

# Test Read from Firestore
def fetch_students():
    students_ref = db.collection('students')
    docs = students_ref.stream()
    for doc in docs:
        print(f"{doc.id} => {doc.to_dict()}")

if __name__ == "__main__":
    print("Fetching students from Firestore...")
    fetch_students()
