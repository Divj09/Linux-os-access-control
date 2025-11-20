import joblib, os
from datetime import datetime

MODEL_FILE = "model.pkl"

def load_model():
    if not os.path.exists(MODEL_FILE):
        raise Exception("model.pkl not found!")
    return joblib.load(MODEL_FILE)

def featurize(uid, filename, action, hour):
    filename = str(filename)

    path_depth = filename.count("/")
    ext_len = len(filename.split(".")[-1]) if "." in filename else 0
    action_flag = 1 if action == "write" else 0

    # NEW 6th FEATURE = hour of day
    return [uid, path_depth, ext_len, action_flag, hour, len(filename)]

def predict_access(clf, uid, filename, action):
    hour = datetime.now().hour
    features = featurize(uid, filename, action, hour)

    pred = clf.predict([features])[0]
    prob = clf.predict_proba([features])[0][1]

    return ("deny" if pred == 1 else "allow", float(prob))