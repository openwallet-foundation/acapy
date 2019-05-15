"""
Enclose property names in double quotes in order to JSON serialize the contents in the API
"""
CUSTOMIZATIONS = {
    "serializers": {
        "Address": {"includeFields": ["id", "city", "province"]},
        "Topic": {
            "includeFields": [
                "id",
                "create_timestamp",
                "update_timestamp",
                "source_id",
                "type",
            ]
        },
    },
    "views": {
        "TopicViewSet": {
            "includeMethods": []
        }
    },
}

SEARCH_TERMS_EXCLUSIVE = True
