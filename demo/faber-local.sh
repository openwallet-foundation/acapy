#!/bin/bash
# this runs the Faber example as a local instace of instance of aca-py
# you need to run a local von-network (in the von-network directory run "./manage start <your local ip> --logs")
# ... and you need to install the local aca-py python libraries locally ("pip install -r ../requriements.txt -r ../requirements.indy.txt -r ../requirements.bbs.txt")

the following will auto-respond on connection and credential requests, but not proof requests
# PYTHONPATH=.. ../bin/aca-py start \
#    --endpoint http://127.0.0.1:8020 \
#    --label faber.agent \
#    --inbound-transport http 0.0.0.0 8020 \
#    --outbound-transport http \
#    --admin 0.0.0.0 8021 \
#    --admin-insecure-mode \
#    --wallet-type indy \
#    --wallet-name faber.agent916333 \
#    --wallet-key faber.agent916333 \
#    --preserve-exchange-records \
#    --auto-provision \
#    --seed FABERDATARDM00000000000000000009
#    --genesis-url http://localhost:9000/genesis \
#    --trace-target log \
#    --trace-tag acapy.events \
#    --trace-label faber.agent.trace \
#    --auto-ping-connection \
#    --auto-respond-messages \
#    --auto-accept-invites \
#    --auto-accept-requests \
#    --auto-respond-credential-proposal \
#    --auto-respond-credential-offer \
#    --auto-respond-credential-request \
#    --auto-store-credential

# PYTHONPATH=.. ../bin/aca-py start \
#    --endpoint http://904e-2a02-908-698-80a0-3c5a-cbec-8ef8-9604.ngrok.io
#    --label faber.agent \
#    --inbound-transport http 0.0.0.0 8020 \
#    --outbound-transport http \
#    --admin 0.0.0.0 8021 \
#    --admin-insecure-mode \
#    --wallet-type indy \
#    --wallet-name faber.agent916333 \
#    --wallet-key faber.agent916333 \
#    --preserve-exchange-records \
#    --auto-provision \
#    --seed FABERDATARDM00000000000000000009
#    --genesis-url http://dev.bcovrin.vonx.io/genesis \
#    --trace-target log \
#    --trace-tag acapy.events \
#    --trace-label faber.agent.trace \
#    --auto-ping-connection \
#    --auto-respond-messages \
#    --auto-accept-invites \
#    --auto-accept-requests \
#    --auto-respond-credential-proposal \
#    --auto-respond-credential-offer \
#    --auto-respond-credential-request \
#    --auto-store-credential

PYTHONPATH=.. ../bin/aca-py start \
   --endpoint https://37aa-43-243-207-194.in.ngrok.io #change to ngrok (run: ngrok http 8020)
   --label faber.agent \
   --inbound-transport http 0.0.0.0 8020 \
   --outbound-transport http \
   --admin 0.0.0.0 8021 \
   --admin-insecure-mode \
   --wallet-type indy \
   --wallet-name faber.agent916333 \
   --wallet-key faber.agent916333 \
   --preserve-exchange-records \
   --auto-provision \
   --seed V6IbU3kqz5w14zWntXKcOKdQDxnsXHtV
   --genesis-url http://dev.greenlight.bcovrin.vonx.io/genesis \
   --trace-target log \
   --trace-tag acapy.events \
   --trace-label faber.agent.trace \
   --auto-ping-connection \
   --auto-respond-messages \
   --auto-accept-invites \
   --auto-accept-requests \
   --auto-respond-credential-proposal \
   --auto-respond-credential-offer \
   --auto-respond-credential-request \
   --auto-store-credential
#   --webhook-url https://3443-2a02-908-699-1d60-35eb-fc7d-d127-e31.ngrok.io/webhooks

set these for full auto
  --auto-respond-presentation-proposal \
  --auto-respond-presentation-request \
  --auto-verify-presentation \
