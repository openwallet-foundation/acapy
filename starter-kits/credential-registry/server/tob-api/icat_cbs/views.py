import logging

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from icat_cbs.utils.credential import Credential, CredentialManager
from icat_cbs.utils.issuer import IssuerManager

LOGGER = logging.getLogger(__name__)

TOPIC_CONNECTIONS = "connections"
TOPIC_CREDENTIALS = "credentials"
TOPIC_PRESENTATIONS = "presentations"
TOPIC_GET_ACTIVE_MENU = "get-active-menu"
TOPIC_PERFORM_MENU_ACTION = "perform-menu-action"
TOPIC_ISSUER_REGISTRATION = "issuer_registration"


@api_view(["POST"])
@permission_classes((permissions.AllowAny,))
def agent_callback(request, topic):
    message = request.data

    # dispatch based on the topic type
    if topic == TOPIC_CONNECTIONS:
        return handle_connections(message["state"], message)

    elif topic == TOPIC_CREDENTIALS:
        return handle_credentials(message["state"], message)

    elif topic == TOPIC_PRESENTATIONS:
        return handle_presentations(message["state"], message)

    elif topic == TOPIC_GET_ACTIVE_MENU:
        return handle_get_active_menu(message)

    elif topic == TOPIC_PERFORM_MENU_ACTION:
        return handle_perform_menu_action(message)

    elif topic == TOPIC_ISSUER_REGISTRATION:
        return handle_register_issuer(message)

    else:
        LOGGER.info("Callback: topic=", topic, ", message=", message)
        return Response("Invalid topic: " + topic, status=status.HTTP_400_BAD_REQUEST)


def handle_connections(state, message):
    # TODO auto-accept?
    print("handle_connections()", state)
    return Response(state)


def handle_credentials(state, message):
    """
    Receives notification of a credential processing event.

    For example, for a greenlight registration credential:
        message = {
            "connection_id": "12345",
            "credential_definition_id": "6qnvgJtqwK44D8LFYnV5Yf:3:CL:25:tag",
            "credential_exchange_id": "666",
            "credential_id": "67890",
            "credential_offer": {},
            "credential_request": {},
            "credential_request_metadata": {},
            "credential": {
                "referent": "67892",
                "values":
                    {
                        "address_line_1": "2230 Holdom Avenue",
                        "address_line_2": "",
                        "addressee": "Ms. Brenda J Strachan",
                        "city": "Surrey",
                        "corp_num": "FM0243624",
                        "country": "CA",
                        "entity_name_effective": "2007-08-30",
                        "entity_status": "Active",
                        "entity_status_effective": "2007-08-30",
                        "entity_type": "BC Company",
                        "legal_name": "LOEFFLER PIZZA PLACE LIMITED",
                        "postal_code": "V3T 4Y5",
                        "province": "BC",
                        "reason_description": "Filing:REGST",
                        "registration_date": "2007-08-30"
                    }, 
                "schema_id": "6qnvgJtqwK44D8LFYnV5Yf:2:Registered Corporation:1.0.3", 
                "cred_def_id": "6qnvgJtqwK44D8LFYnV5Yf:3:CL:25:tag", 
                "rev_reg_id": null, 
                "rev_reg": null, 
                "witness": "Ian",
                "cred_rev_id": null,
                "signature": "ian costanzo, honest",
                "signature_correctness_proof": "honest"
            },
            "initiator": "...",
            "schema_id": "...",
            "state": "stored",
            "thread_id": "..."
        }
    """
    # global admin_url
    credential_exchange_id = message["credential_exchange_id"]
    print(
        "Credential: state=", state, ", credential_exchange_id=", credential_exchange_id
    )

    if state == "offer_received":
        print("After receiving credential offer, send credential request")
        # resp = requests.post(admin_url + '/credential_exchange/' + credential_exchange_id + '/send-request')
        # assert resp.status_code == 200
        return Response("")

    elif state == "stored":
        print("After stored credential in wallet")
        # TBD credential info should come with the message
        # resp = requests.get(admin_url + '/credential/' + message['credential_id'])
        # assert resp.status_code == 200
        print("Stored credential:")
        print(message["credential"])
        print("credential_id", message["credential_id"])
        print("credential_definition_id", message["credential_definition_id"])
        print("schema_id", message["schema_id"])
        print("credential_request_metadata", message["credential_request_metadata"])

        credential_data = message["credential"]

        LOGGER.info(credential_data)

        credential = Credential(credential_data, wallet_id=credential_data["referent"])
        credential_manager = CredentialManager()
        credential_manager.process(credential)

        return Response({"success": True, "result": credential_data["referent"]})

    # TODO other scenarios
    return Response("")


def handle_presentations(state, message):
    # TODO auto-respond to proof requests
    print("handle_presentations()", state)
    return Response(some_data)


def handle_get_active_menu(message):
    # TODO add/update issuer info?
    print("handle_get_active_menu()", message)
    return Response("")


def handle_perform_menu_action(message):
    # TODO add/update issuer info?
    print("handle_perform_menu_action()", message)
    return Response("")


def handle_register_issuer(message):
    """Handles the registration of a new issuing agent in the credential registry.
       
       The agent registration credential will be in the following format:
       {
            "issuer_registration_id": "string",
            "connection_id": "string",
            "issuer_registration": {
                "credential_types": [
                {
                    "category_labels": ["string"],
                    "claim_descriptions": ["string"],
                    "credential_def_id": "string",
                    "name": "string",
                    "credential": "string",
                    "topic": "string",
                    "endpoint": "string",
                    "cardinality_fields": [{}],
                    "mapping": {},
                    "version": "string",
                    "visible_fields": ["string"],
                    "description": "string",
                    "logo_b64": "string",
                    "schema": "string",
                    "claim_labels": ["string"]
                }
                ],
                "issuer": {
                "name": "string",
                "did": "string",
                "abbreviation": "string",
                "email": "string",
                "url": "string",
                "endpoint": "string",
                "logo_b64": "string"
                }
            },
            "initiator": "self",
            "state": "registration_sent"
        }
    """
    issuer_manager = IssuerManager()
    updated = issuer_manager.register_issuer(message)
    return Response(content_type="application/json", data={"result": updated})
