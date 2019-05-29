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
        "TopicRelationship": {
            "includeFields": [
                "id",
                "credential",
                "topic",
                "related_topic",
            ]
        },
    },
    "views": {
        "TopicViewSet": {
            "includeMethods": []
        },
        "TopicRelationshipViewSet": {
            "includeMethods": []
        }
    },
}

SEARCH_TERMS_EXCLUSIVE = True

API_METADATA = {
    "title": "OrgBook ON API",
    "description":
        "OrgBook ON is a public, searchable directory of digital records for registered "
        "businesses in the Province of Ontario. Over time, other government "
        "organizations and businesses will also begin to issue digital records through "
        "OrgBook ON. For example, permits and licenses issued by various government services.",
    "terms": {
        "url": "https://www.ontario.ca/page/terms-use",
    },
    "contact": {
        "url": "https://www.ontario.ca/feedback/contact-us?id=26922&nid=72703",
    },
    "license": {
        "name": "Open Government License - Ontario",
        "url": "https://www.ontario.ca/page/open-government-licence-ontario",
    },
}
