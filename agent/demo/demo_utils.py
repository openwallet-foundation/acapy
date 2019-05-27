import subprocess
import time
import threading
import os
import json
import web
import logging


####################################################
# run background services to receive web hooks
####################################################
# agent webhook callbacks
class webhooks:
    def GET(self, topic):
        # just for testing; all indy-cat agent hooks are POST requests
        s_print("GET: topic=", topic)
        return ""

    def POST(self, topic):
        message = json.loads(web.data())

        # dispatch based on the topic type
        if topic == "connections":
            return self.handle_connections(message["state"], message)

        elif topic == "credentials":
            return self.handle_credentials(message["state"], message)

        elif topic == "presentations":
            return self.handle_presentations(message["state"], message)

        elif topic == "get-active-menu":
            return self.handle_get_active_menu(message)

        elif topic == "perform-menu-action":
            return self.handle_perform_menu_action(message)

        else:
            s_print("Callback: topic=", topic, ", message=", message)
            return ""

            return self.handle_connections(message["state"], message)

    def handle_connections(self, state, message):
        conn_id = message["connection_id"]
        s_print("Connection: state=", state, ", connection_id=", conn_id)
        return ""

    def handle_credentials(self, state, message):
        credential_exchange_id = message["credential_exchange_id"]
        s_print(
            "Credential: state=",
            state,
            ", credential_exchange_id=",
            credential_exchange_id,
        )
        return ""

    def handle_presentations(self, state, message):
        presentation_exchange_id = message["presentation_exchange_id"]
        s_print(
            "Presentation: state=",
            state,
            ", presentation_exchange_id=",
            presentation_exchange_id,
        )
        return ""

    def handle_get_active_menu(self, message):
        s_print("Get active menu: message=", message)
        return ""

    def handle_perform_menu_action(self, message):
        s_print("Handle menu action: message=", message)
        return ""


def background_hook_service(urls, g_vars):
    # run app and respond to agent webhook callbacks (run in background)
    # port number has to be the first command line arguement
    # pass in urls
    app = web.application(urls, g_vars)
    app.run()


def background_hook_thread(urls, g_vars):
    # run app and respond to agent webhook callbacks (run in background)
    webhook_thread = threading.Thread(
        target=background_hook_service, args=(urls, g_vars)
    )
    webhook_thread.daemon = True
    webhook_thread.start()
    print("Web hooks is running!")
    return webhook_thread


####################################################
# run indy-cat agent as a sub-process
####################################################
s_print_lock = threading.Lock()


def s_print(*a, **b):
    """Thread safe print function"""
    with s_print_lock:
        print(*a, **b)


def output_reader(proc):
    for line in iter(proc.stdout.readline, b""):
        s_print("got line: {0}".format(line.decode("utf-8")), end="")
        pass


def stderr_reader(proc):
    for line in iter(proc.stderr.readline, b""):
        s_print("got line: {0}".format(line.decode("utf-8")), end="")
        pass


def start_agent_subprocess(
    genesis,
    seed,
    endpoint_url,
    in_port_1,
    in_port_2,
    in_port_3,
    admin_port,
    wallet_type,
    wallet_name,
    wallet_key,
    python_path,
    webhook_url,
):
    my_env = os.environ.copy()
    my_env["PYTHONPATH"] = python_path

    # start and expose a REST callback service
    my_env["WEBHOOK_URL"] = webhook_url
    print("Webhook url is at", my_env["WEBHOOK_URL"])

    # start agent sub-process
    agent_proc = subprocess.Popen(
        [
            "python3",
            "../scripts/icatagent",
            "--inbound-transport",
            "http",
            "0.0.0.0",
            str(in_port_1),
            "--inbound-transport",
            "http",
            "0.0.0.0",
            str(in_port_2),
            "--inbound-transport",
            "ws",
            "0.0.0.0",
            str(in_port_3),
            "--endpoint",
            endpoint_url,
            "--outbound-transport",
            "ws",
            "--outbound-transport",
            "http",
            "--genesis-transactions",
            genesis,
            "--auto-respond-messages",
            "--accept-invites",
            "--accept-requests",
            "--wallet-type",
            wallet_type,
            "--wallet-name",
            wallet_name,
            "--wallet-key",
            wallet_key,
            "--seed",
            seed,
            "--admin",
            "0.0.0.0",
            str(admin_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=my_env,
    )
    time.sleep(0.5)
    t1 = threading.Thread(target=output_reader, args=(agent_proc,))
    t1.start()
    t2 = threading.Thread(target=stderr_reader, args=(agent_proc,))
    t2.start()

    return (agent_proc, t1, t2)
