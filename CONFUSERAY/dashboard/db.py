from pymongo import MongoClient

def get_db(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=5000)["depguard"]

def save_report(db, report):
    result = db.reports.insert_one(dict(report))
    return str(result.inserted_id)

def get_reports_index(db):
    """oldest first"""
    cursor = db.reports.find(
        {}, {"generated_at": 1, "total_findings": 1, "summary": 1, "meta": 1}
    ).sort("generated_at", 1)
    return [
        {
            "file": str(doc["_id"]),
            "generated_at": doc.get("generated_at", ""),
            "total_findings": doc.get("total_findings", 0),
            "summary": doc.get("summary", {}),
            "meta": doc.get("meta", {}),
        }
        for doc in cursor
    ]


def get_report(db, report_id):
    from bson import ObjectId
    try:
        oid = ObjectId(report_id)
    except Exception:
        return None
    doc = db.reports.find_one({"_id": oid})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc
