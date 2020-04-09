
import csv

from elasticsearch_dsl import connections
from elasticsearch_dsl import Search


connections.create_connection(hosts=['localhost'], timeout=20)

s = Search(index='fluentd-*')
s = s.sort('timestamp')
# only return the selected fields
s = s.source(['str_time', 'timestamp', 'handler', 'ellapsed_milli', 'thread_id', 'msg_id', 'outcome', 'traced_type'])
#response = s.execute()
#print('Total hits found:', response.hits.total)
with open('agent-events.csv', 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile)
    i = 0
    spamwriter.writerow(["idx", "str_time", "timestamp", "handler", "ellapsed_milli", "thread_id", "msg_id", "outcome", "traced_type"])
    for x in s.scan():
        i = i + 1
        spamwriter.writerow([i, x.str_time, x.timestamp, x.handler, x.ellapsed_milli, x.thread_id, x.msg_id, x.outcome, x.traced_type])
