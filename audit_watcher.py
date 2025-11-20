#!/usr/bin/env python3
# audit_watcher.py — FINAL CLEAN VERSION

import re, os, time, requests
from datetime import datetime
from detect import load_model, predict_access

AUDIT_LOG = "/var/log/audit/audit.log"

RE_AUDIT_ID = re.compile(r"audit\(\d+\.\d+:(\d+)\)")
RE_UID = re.compile(r"\buid=(\d+)\b")
RE_AUID = re.compile(r"\bauid=(\d+)\b")
RE_NAME = re.compile(r'name="([^"]+)"')
RE_PATH = re.compile(r'path="([^"]+)"')
RE_SYSCALL = re.compile(r"syscall=(\w+)")
RE_TYPE_PATH = re.compile(r"\btype=PATH\b")
RE_TYPE_SYSCALL = re.compile(r"\btype=SYSCALL\b")

SYSCALL_ACTION_MAP = {
    "open": "read",
    "openat": "read",
    "read": "read",
    "write": "write",
    "creat": "write",
    "unlink": "write",
    "execve": "exec",
}

LOCAL_INGEST_URL = "http://127.0.0.1:5000/ingest_event"

events = {}

# Paths to ignore (massive noise)
IGNORE_LIST = [
    "/usr", "/lib", "/proc", "/sys", "/run",
    "/snap", "/var/log/audit", "firefox", "cache"
]

def safe_tail(path):
    """Follow only NEW lines, ignore old and rotated logs."""
    f = open(path, "r", errors="ignore")
    f.seek(0, os.SEEK_END)

    inode = os.fstat(f.fileno()).st_ino

    while True:
        line = f.readline()
        if line:
            yield line
            continue

        # Detect rotation
        try:
            if os.stat(path).st_ino != inode:
                f.close()
                f = open(path, "r", errors="ignore")
                f.seek(0, os.SEEK_END)
                inode = os.fstat(f.fileno()).st_ino
        except:
            pass

        time.sleep(0.1)

def process_event(eid, rec, clf):
    uid = rec.get("uid", 0)
    auid = rec.get("auid", 0)
    filename = str(rec.get("filename", "unknown"))
    action = rec.get("action", "read")

    decision, probability = predict_access(clf, uid, filename, action)

    print(f"[{datetime.now().isoformat()}] UID={uid} FILE={filename} ACTION={action} -> {decision} (prob={probability:.3f})")

    payload = {
        "timestamp": int(time.time() * 1000),
        "uid": uid,
        "auid": auid,
        "filename": filename,
        "action": action,
        "decision": decision,
        "probability": probability,
    }

    try:
        requests.post(LOCAL_INGEST_URL, json=payload, timeout=0.2)
    except:
        pass

def main():
    print("Starting audit_watcher... (clean mode)")
    clf = load_model()

    for line in safe_tail(AUDIT_LOG):
        m = RE_AUDIT_ID.search(line)
        if not m:
            continue
        eid = m.group(1)

        if eid not in events:
            events[eid] = {}

        if RE_TYPE_SYSCALL.search(line):
            uid_m = RE_UID.search(line)
            auid_m = RE_AUID.search(line)
            call_m = RE_SYSCALL.search(line)

            if uid_m: events[eid]["uid"] = int(uid_m.group(1))
            if auid_m: events[eid]["auid"] = int(auid_m.group(1))
            if call_m:
                events[eid]["action"] = SYSCALL_ACTION_MAP.get(call_m.group(1), "read")

        if RE_TYPE_PATH.search(line):
            m_name = RE_NAME.search(line)
            m_path = RE_PATH.search(line)

            if m_name:
                events[eid]["filename"] = m_name.group(1)
            elif m_path:
                events[eid]["filename"] = m_path.group(1)

        # Wait until full event is ready
        if "uid" in events[eid] and "action" in events[eid] and "filename" in events[eid]:

            # IGNORE SPAM
            fn = events[eid]["filename"]
            if any(x in fn for x in IGNORE_LIST):
                del events[eid]
                continue

            # SLOW DOWN speed (dashboard-friendly)
            time.sleep(0.15)

            process_event(eid, events[eid], clf)
            del events[eid]

if __name__ == "__main__":
    main()
