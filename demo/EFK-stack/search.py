import csv

from elasticsearch_dsl import connections
from elasticsearch_dsl import Search


connections.create_connection(hosts=["localhost"], timeout=20)

s = Search(index="fluentd-*")
# only return the selected fields
s = s.source(
    [
        "str_time",
        "timestamp",
        "handler",
        "ellapsed_milli",
        "thread_id",
        "msg_id",
        "outcome",
        "traced_type",
    ]
)
s = s.sort("timestamp")
events = []
for x in s.scan():
    events.append(
        {
            "str_time": x.str_time,
            "timestamp": x.timestamp,
            "handler": x.handler,
            "ellapsed_milli": x.ellapsed_milli,
            "thread_id": x.thread_id,
            "msg_id": x.msg_id,
            "outcome": x.outcome,
            "traced_type": x.traced_type,
        }
    )
sorted_events = sorted(events, key=lambda i: i["timestamp"])

threads = {}
thread_count = 0
agents = {}
with open("agent-events.csv", "w", newline="") as csvfile:
    spamwriter = csv.writer(csvfile)
    i = 0
    spamwriter.writerow(
        [
            "idx",
            "str_time",
            "timestamp",
            "handler",
            "ellapsed_milli",
            "thread_id",
            "msg_id",
            "outcome",
            "traced_type",
            "delta_agent",
            "delta_thread",
        ]
    )
    for x in sorted_events:
        if x["handler"] in agents:
            delta_agent = x["timestamp"] - agents[x["handler"]]
            if delta_agent < 0:
                print(i, delta_agent)
        else:
            delta_agent = 0
        agents[x["handler"]] = x["timestamp"]
        if x["thread_id"] in threads:
            delta_thread = x["timestamp"] - threads[x["thread_id"]]
            if delta_thread < 0:
                print(i, delta_thread)
        else:
            delta_thread = 0
            thread_count = thread_count + 1
        threads[x["thread_id"]] = x["timestamp"]
        i = i + 1
        spamwriter.writerow(
            [
                i,
                x["str_time"],
                x["timestamp"],
                x["handler"],
                x["ellapsed_milli"],
                x["thread_id"],
                x["msg_id"],
                x["outcome"],
                x["traced_type"],
                delta_agent,
                delta_thread,
            ]
        )

print("Total threads=", thread_count)
