# quick_train.py
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier

# Synthetic training dataset
# Columns: uid, filename, action, hour, suspicious (0 or 1)
data = [
    (0, "/etc/passwd", "read", 10, 0),
    (1000, "/home/user/docs/report.txt", "read", 14, 0),
    (1001, "/home/user/secret.txt", "read", 3, 1),
    (1004, "/home/user/private/passwd_backup", "read", 2, 1),
    (1002, "/tmp/tmpfile", "write", 9, 0),
    (1003, "/home/user/confidential/data.txt", "read", 1, 1),
    (2000, "/var/log/syslog", "read", 16, 0),
    (1999, "/home/user/private/keys.txt", "read", 4, 1),
    (1500, "/home/user/myfile.txt", "write", 18, 0),
    (1600, "/etc/shadow", "read", 2, 1),
]

df = pd.DataFrame(data, columns=["uid","filename","action","hour","suspicious"])

# Feature extraction
def featurize(r):
    path_depth = r['filename'].count("/")
    path_len = len(r['filename'])
    sensitive = int(any(k in r['filename'].lower() for k in 
                        ["secret","passwd","etc","private","shadow","confidential"]))
    act_code = 1 if r['action']=="read" else 2 if r['action']=="write" else 0
    return [int(r['uid']), path_depth, path_len, sensitive, int(r['hour']), act_code]

X = np.array([featurize(r) for _,r in df.iterrows()])
y = df['suspicious'].values

# Train classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X, y)

# Save model
joblib.dump(clf, "model.pkl")
print("✔ Model trained and saved as model.pkl")